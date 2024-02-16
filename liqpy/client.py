from warnings import warn
from typing import Optional, Literal, Union, TYPE_CHECKING, Unpack, AnyStr, Type
from os import environ
from logging import getLogger
from datetime import datetime, timedelta
from numbers import Number
from re import search
from uuid import UUID

from requests import Session
from secret_type import secret, Secret

from liqpy import __version__
from liqpy.dev import LiqPyWarning

from .api import (
    VERSION,
    Endpoint,
    post,
    sign,
    request,
    encode,
    decode,
    is_sandbox,
    exception,
    BasePreprocessor,
    BaseValidator,
    JSONEncoder,
    JSONDecoder,
    Decoder,
)

if TYPE_CHECKING:
    from .types.common import Language, Currency, SubscribePeriodicity, PayOption
    from .types.request import Format, Language, LiqpayRequestDict
    from .types.callback import LiqpayCallbackDict, LiqpayRefundDict


__all__ = ["Client"]


logger = getLogger(__package__)


CHECKOUT_ACTIONS = (
    "auth",
    "pay",
    "hold",
    "subscribe",
    "paydonate",
)


class Client:
    """
    [LiqPay API](https://www.liqpay.ua/en/documentation/api/home) authorized client.

    Intialize by setting environment variables `LIQPAY_PUBLIC_KEY` and `LIQPAY_PRIVATE_KEY`:
    >>> client = Client()  # doctest: +SKIP

    Or pass them as arguments:
    >>> Client(public_key="i00000000", private_key="a4825234f4bae72a0be04eafe9e8e2bada209255")
    Client(public_key="i00000000")

    For using custom [session](https://requests.readthedocs.io/en/stable/api/#request-sessions)
    pass it as an keyword argument:
    >>> with Session() as session:  # doctest: +SKIP
    >>>     client = Client(session=session) # doctest: +SKIP

    Client implements context manager interface:
    >>> with Client() as client:  # doctest: +SKIP
    >>>     pass  # doctest: +SKIP
    >>> # client.session is closed
    """

    _session: Session
    _public_key: str
    _private_key: Secret[bytes]

    validator: Optional[BaseValidator] = None
    preprocessor: Optional[BasePreprocessor] = None
    encoder: Optional[JSONEncoder] = None
    decoder: Optional[JSONDecoder] = None

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        session: Session = None,
        validator: Optional[BaseValidator] = None,
        preprocessor: Optional[BasePreprocessor] = None,
        encoder: Optional[JSONEncoder] = None,
        decoder: Optional[Type[JSONDecoder]] = None,
    ):
        self.update_keys(public_key=public_key, private_key=private_key)
        self.session = session

        self.validator = validator
        self.preprocessor = preprocessor
        self.encoder = encoder
        self.decoder = decoder

    @property
    def public_key(self) -> str:
        """Public key used for requests"""
        return self._public_key

    @property
    def sandbox(self) -> bool:
        """Check if client use sandbox LiqPay API"""
        return is_sandbox(self._public_key)

    @property
    def session(self) -> Session:
        """
        Session object used for requests

        For advanced usage see: https://docs.python-requests.org/en/latest/user/advanced/#session-objects
        """
        return self._session

    @session.setter
    def session(self, /, session: Optional[Session]):
        if session is None:
            session = Session()
        else:
            assert isinstance(
                session, Session
            ), "Session must be an instance of `requests.Session`"

        session.headers.update({"User-Agent": f"{__package__}/{__version__}"})
        self._session = session

    def update_keys(
        self, /, *, public_key: str | None, private_key: str | None
    ) -> None:
        """Update public and private keys"""
        if public_key is None:
            public_key = environ["LIQPAY_PUBLIC_KEY"]

        if private_key is None:
            private_key = environ["LIQPAY_PRIVATE_KEY"]

        sandbox = is_sandbox(public_key)
        if sandbox != is_sandbox(private_key):
            raise ValueError("Public and private keys must be both sandbox or both not")

        self._public_key = public_key
        self._private_key = secret(private_key.encode())

        warn(
            "Using %s LiqPay API" % ("sandbox" if sandbox else "live"),
            stacklevel=2,
            category=LiqPyWarning,
        )

    def __repr__(self):
        return f'{self.__class__.__name__}(public_key="{self._public_key}")'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._session.close()

    def __del__(self):
        self._session.close()

    def _callback(
        self, /, data: bytes, signature: bytes, *, verify: bool = True
    ) -> "LiqpayCallbackDict":
        if verify:
            self.verify(data, signature)
        else:
            logger.warning("Skipping LiqPay signature verification")

        return decode(data)

    def sign(self, data: bytes, /) -> bytes:
        """
        Sign data string with private key

        See `liqpy.api.sign` for more information.
        """
        with self._private_key.dangerous_reveal() as pk:
            return sign(data, key=pk)

    def encode(
        self, /, action: str, **kwargs: Unpack["LiqpayRequestDict"]
    ) -> tuple[bytes, bytes]:
        """
        Encode parameters into data and signature strings

        >>> data, signature = client.encode("status", order_id="a1a1a1a1")

        See `liqpy.api.encode` for more information.
        """
        data = encode(
            request(action, public_key=self._public_key, version=VERSION, **kwargs),
            filter_none=True,
            validator=self.validator,
            preprocessor=self.preprocessor,
            encoder=self.encoder,
        )
        signature = self.sign(data)

        return data, signature

    def is_valid(self, /, data: bytes, signature: bytes) -> bool:
        """
        Check if the signature is valid

        Used for verification in `liqpy.Client.verify`.
        """
        return self.sign(data) == signature

    def verify(self, /, data: bytes, signature: bytes) -> None:
        """
        Verify data signature

        Raises an `AssertionError` if `data` does not match the `signature`.

        Used for verification in `liqpy.Client.callback`.
        """
        assert self.is_valid(data, signature), "Invalid signature"

    def request(self, action: str, **kwargs: "LiqpayRequestDict") -> dict:
        """
        Make a Server-Server request to LiqPay API
        """
        response = post(
            Endpoint.REQUEST,
            *self.encode(action, **kwargs),
            session=self._session,
            allow_redirects=False,
            stream=False,
        )

        if not response.headers.get("Content-Type", "").startswith("application/json"):
            raise exception(response=response)

        data: dict = response.json(cls=self.decoder or Decoder)

        result: Optional[Literal["ok", "error"]] = data.pop("result", None)
        status = data.get("status")
        err_code = data.pop("err_code", None) or data.pop("code", None)

        if result == "ok":
            return data

        if action in ("status", "data") and data.get("payment_id") is not None:
            return data

        if status in ("error", "failure") or result == "error":
            raise exception(
                code=err_code,
                description=data.pop("err_description", None),
                response=response,
                details=data,
            )

        return data

    def pay(
        self,
        /,
        amount: Number,
        order_id: str | UUID,
        card: str,
        currency: "Currency",
        description: str,
        **kwargs: "LiqpayRequestDict",
    ) -> "LiqpayCallbackDict":
        """
        Request a `pay` action from LiqPay API

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/pay/doc)
        """
        return self.request(
            "pay",
            order_id=order_id,
            amount=amount,
            card=card,
            currency=currency,
            description=description,
            **kwargs,
        )

    def unsubscribe(self, /, order_id: str | UUID) -> "LiqpayCallbackDict":
        """
        Cancel recurring payments for the order

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/unsubscribe/doc)
        """
        return self.request("unsubscribe", order_id=order_id)

    def refund(
        self,
        /,
        payment_id: int | None = None,
        *,
        order_id: str | UUID | None = None,
        amount: Number | None = None,
    ) -> "LiqpayRefundDict":
        """
        Make a refund request to LiqPay API

        For recurring payments `payment_id` parameter is required, in other cases use `order_id`.
        """
        match (order_id, payment_id):
            case (_, payment_id) if payment_id is not None:
                return self.request("refund", payment_id=str(payment_id), amount=amount)
            case (order_id, None) if order_id is not None:
                return self.request("refund", order_id=order_id, amount=amount)
            case (None, None):
                raise ValueError("`order_id` or `payment_id` must be provided")

    def complete(
        self, /, order_id: str | UUID, *, amount: Number | None = None
    ) -> "LiqpayCallbackDict":
        """
        Request a `hold_completion` action from LiqPay API

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/hold_completion/doc)
        """
        return self.request("hold_completion", order_id=order_id, amount=amount)

    def checkout(
        self,
        action: Literal["auth", "pay", "hold", "subscribe", "paydonate"],
        /,
        order_id: str | UUID,
        amount: Number,
        currency: "Currency",
        description: str,
        expired_date: str | datetime | timedelta | None = None,
        paytypes: Optional[list["PayOption"]] = None,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> str:
        """
        Make a Client-Server checkout request to LiqPay API

        Returns a url to redirect the user to.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/checkout/doc)
        """
        assert (
            action in CHECKOUT_ACTIONS
        ), "Invalid action. Must be one of: %s" % ",".join(CHECKOUT_ACTIONS)

        response = post(
            Endpoint.CHECKOUT,
            *self.encode(
                action,
                order_id=order_id,
                amount=amount,
                currency=currency,
                description=description,
                expired_date=expired_date,
                paytypes=paytypes,
                **kwargs,
            ),
            session=self._session,
            allow_redirects=False,
        )

        next = response.next

        if next is None:
            result = {}
            if response.headers.get("Content-Type", "").startswith("application/json"):
                result = response.json()

            raise exception(
                code=result.pop("err_code", None),
                description=result.pop("err_description", None),
                response=response,
                details=result if len(result) else None,
            )

        return next.url

    def payments(
        self,
        /,
        date_from: Union[datetime, str, int, timedelta],
        date_to: Union[datetime, str, int, timedelta],
    ) -> list["LiqpayCallbackDict"]:
        """
        Get an archive of recieved payments

        For a significant amount of data use `liqpy.client.Client.reports` with `csv` format instead.
        """
        result = self.reports(date_from, date_to, format="json")
        return Decoder().decode(result)

    def reports(
        self,
        /,
        date_from: Union[datetime, str, int, timedelta],
        date_to: Union[datetime, str, int, timedelta],
        *,
        format: Optional["Format"] = None,
    ) -> str:
        """
        Get an archive of recieved payments

        Example to get a json archive for the last 30 days:
        >>> from datetime import datetime, timedelta
        >>> from liqpy.client import Client
        >>> from liqpy.constants import LIQPAY_TZ
        >>> client = Client()
        >>> date_to = datetime.now(LIQPAY_TZ)
        >>> date_from = date_to - timedelta(days=30)
        >>> result = client.reports(date_from, date_to, format="csv")
        >>> print(result)

        [Documentaion](https://www.liqpay.ua/en/documentation/api/information/reports/doc)
        """
        response = post(
            Endpoint.REQUEST,
            *self.encode(
                "reports", date_from=date_from, date_to=date_to, resp_format=format
            ),
            session=self._session,
        )

        output: str = response.text
        error: dict | None = None

        content_type = response.headers.get("Content-Type", "")

        if content_type.startswith("application/json"):
            if format == "json" or format is None:
                s = search(r'"data":(\[(.*)\])\}$', output)
                if s is not None:
                    output = s.group(1)
                else:
                    error = response.json()

            else:
                error = response.json()

        if error is None:
            return output
        else:
            raise exception(
                code=error.pop("err_code", None) or error.pop("code", None),
                description=error.pop("err_description", ""),
                response=response,
                details=error,
            )

    def subscribe(
        self,
        /,
        order_id: str | UUID,
        amount: Number,
        card: str,
        card_cvv: str,
        card_exp_month: str,
        card_exp_year: str,
        currency: "Currency",
        description: str,
        subscribe_periodicity: "SubscribePeriodicity",
        subscribe_date_start: datetime | str | timedelta | None | Number,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> "LiqpayCallbackDict":
        """
        Create an order with recurring payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/subscribe/doc)
        """
        return self.request(
            "subscribe",
            order_id=order_id,
            amount=amount,
            card=card,
            card_cvv=card_cvv,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            currency=currency,
            description=description,
            subscribe_date_start=subscribe_date_start,
            subscribe_periodicity=subscribe_periodicity,
            **kwargs,
        )

    def data(self, /, order_id: str, info: str) -> "LiqpayCallbackDict":
        """
        Adding an info to already created payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/data/doc)
        """
        return self.request("data", order_id=order_id, info=info)

    def receipt(
        self,
        /,
        order_id: str,
        email: str,
        *,
        payment_id: Optional[int] = None,
        language: Optional["Language"] = None,
    ) -> None:
        """
        Send a receipt to the customer

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/ticket/doc)
        """
        self.request(
            "receipt",
            order_id=order_id,
            email=email,
            payment_id=payment_id,
            language=language,
        )

    def status(self, order_id: str | UUID, /) -> "LiqpayCallbackDict":
        """
        Get the status of a payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/status/doc)
        """
        return self.request("status", order_id=order_id)

    def callback(self, /, data: AnyStr, signature: AnyStr, *, verify: bool = True):
        """
        Verify and decode the callback data

        Example:
        >>> client = Client()
        >>> # get data and signature from webhook request body
        >>> order_id = "a1a1a1a1a1"
        >>> data, signature = client.encode(
        ...     action="pay",
        ...     amount=1,
        ...     order_id=order_id,
        ...     description="Test Encoding",
        ...     currency="USD",
        ... )
        >>> # verify and decode data
        >>> result = client.callback(data, signature)
        >>> assert result["order_id"] == order_id
        >>> assert result["action"] == "pay"
        >>> assert result["amount"] == 1
        >>> assert result["currency"] == "USD"
        >>> assert result["description"] == "Test Encoding"

        [Documentation](https://www.liqpay.ua/en/documentation/api/callback)
        """
        if isinstance(data, str):
            data = data.encode()

        if isinstance(signature, str):
            signature = signature.encode()

        result = self._callback(data, signature, verify=verify)
        version = result.get("version")

        if version != VERSION:
            logger.warning("Callback version mismatch: %s != %s", version, VERSION)

        return result
