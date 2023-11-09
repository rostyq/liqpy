from typing import Optional, Literal, Union, TYPE_CHECKING, Unpack, AnyStr
from os import environ
from logging import getLogger
from datetime import datetime, timedelta
from numbers import Number
from re import search
from uuid import UUID

from requests import Session
from secret_type import secret, Secret

from liqpy import __version__

from .api import post, Endpoint, sign, request, encode, decode, VERSION, is_sandbox
from .exceptions import exception_factory
from .data import LiqpayCallback

if TYPE_CHECKING:
    from json import JSONEncoder

    from .preprocess import BasePreprocessor
    from .validation import BaseValidator

    from .types.common import Language, Currency, SubscribePeriodicity, PayOption
    from .types.request import Format, Language, LiqpayRequestDict
    from .types.callback import LiqpayCallbackDict


__all__ = ["Client"]


logger = getLogger(__name__)


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

    validator: Optional["BaseValidator"] = None
    preprocessor: Optional["BasePreprocessor"] = None
    encoder: Optional["JSONEncoder"] = None

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        session: Session = None,
        validator: Optional["BaseValidator"] = None,
        preprocessor: Optional["BasePreprocessor"] = None,
        encoder: Optional["JSONEncoder"] = None,
    ):
        self.update_keys(public_key=public_key, private_key=private_key)
        self.session = session

        self.validator = validator
        self.preprocessor = preprocessor
        self.encoder = encoder

    @property
    def public_key(self) -> str:
        """Public key used for requests."""
        return self._public_key

    @property
    def sandbox(self) -> bool:
        """Check if client use sandbox LiqPay API."""
        return is_sandbox(self._public_key)

    @property
    def session(self) -> Session:
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
        """Update public and private keys."""
        if public_key is None:
            public_key = environ["LIQPAY_PUBLIC_KEY"]

        if private_key is None:
            private_key = environ["LIQPAY_PRIVATE_KEY"]

        sandbox = is_sandbox(public_key)
        if sandbox != is_sandbox(private_key):
            raise ValueError("Public and private keys must be both sandbox or both not")

        self._public_key = public_key
        self._private_key = secret(private_key.encode())

        if sandbox:
            logger.warning("Using sandbox LiqPay API.")

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
        Sign data string with private key.

        See `liqpy.api.sign` for more information.
        """
        with self._private_key.dangerous_reveal() as pk:
            return sign(data, key=pk)

    def encode(
        self, /, action: str, **kwargs: Unpack["LiqpayRequestDict"]
    ) -> tuple[bytes, bytes]:
        """
        Encode parameters into data and signature strings.

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
        Check if the signature is valid.
        Used for verification in `liqpy.Client.verify`.
        """
        return self.sign(data) == signature

    def verify(self, /, data: bytes, signature: bytes) -> None:
        """
        Verify if the signature is valid. Raise an `AssertionError` if not.
        Used for verification in `liqpy.Client.callback`.
        """
        assert self.is_valid(data, signature), "Invalid signature"

    def request(self, action: str, **kwargs: "LiqpayRequestDict") -> dict:
        """
        Make a Server-Server request to LiqPay API.
        """
        response = post(
            Endpoint.REQUEST,
            *self.encode(action, **kwargs),
            session=self._session,
            allow_redirects=False,
            stream=False,
        )

        if not response.headers.get("Content-Type", "").startswith("application/json"):
            raise exception_factory(response=response)

        data: dict = response.json()

        result: Optional[Literal["ok", "error"]] = data.pop("result", None)
        status = data.get("status")
        err_code = data.pop("err_code", data.pop("code", None))

        if result == "ok" or (action in ("status", "data") and err_code is None):
            return data

        if status in ("error", "failure") or result == "error":
            raise exception_factory(
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
    ) -> dict:
        return self.request(
            "pay",
            order_id=order_id,
            amount=amount,
            card=card,
            currency=currency,
            description=description,
            **kwargs,
        )

    def unsubscribe(self, /, order_id: str | UUID) -> dict:
        return self.request("unsubscribe", order_id=order_id)

    def refund(self, /, order_id: str | UUID, amount: Number) -> dict:
        return self.request("refund", order_id=order_id, amount=amount)

    def checkout(
        self,
        action: Literal["auth", "pay", "hold", "subscribe", "paydonate"],
        /,
        order_id: str | UUID,
        amount: Number,
        currency: "Currency",
        description: str,
        expired_date: str | datetime | None = None,
        paytypes: Optional[list["PayOption"]] = None,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> str:
        """
        Make a Client-Server checkout request to LiqPay API.

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

            raise exception_factory(
                code=result.pop("err_code", None),
                description=result.pop("err_description", None),
                response=response,
                details=result if len(result) else None,
            )

        return next.url

    def reports(
        self,
        /,
        date_from: Union[datetime, str, int],
        date_to: Union[datetime, str, int],
        *,
        format: Optional["Format"] = None,
    ) -> str:
        """
        Get an archive of recieved payments.

        Example to get a json archive for the last 30 days:
        >>> import json
        >>> from datetime import datetime, timedelta, UTC
        >>> from liqpy.client import Client
        >>> client = Client()
        >>> date_to = datetime.now(UTC)
        >>> date_from = date_to - timedelta(days=30)
        >>> data = client.reports(date_from, date_to, format="json")
        >>> data = json.loads(data)
        >>> print(len(data), "payments")

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
            if format == "json":
                s = search(r'"data":(\[(.+?)\])', response.text)
                if s is not None:
                    output = s.group(1)
                else:
                    error = response.json()

            else:
                error = response.json()

        if error is None:
            return output
        else:
            raise exception_factory(
                code=error.pop("err_code"),
                description=error.pop("err_description"),
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
    ) -> dict:
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

    def data(self, /, order_id: str, info: str) -> dict:
        """
        Adding an info to already created payment.

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
        Send a receipt to the customer.

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/ticket/doc)
        """
        self.request(
            "receipt",
            order_id=order_id,
            email=email,
            payment_id=payment_id,
            language=language,
        )

    def status(self, order_id: str | UUID, /) -> dict:
        """
        Get the status of a payment.

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/status/doc)
        """
        return self.request("status", order_id=order_id)

    def callback(self, /, data: AnyStr, signature: AnyStr, *, verify: bool = True):
        """
        Verify and decode the callback data.

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

        try:
            return LiqpayCallback(**result)
        finally:
            logger.warning("Failed to parse callback data.", extra=result)
