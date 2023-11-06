from typing import Optional, Literal, Union, TYPE_CHECKING, Iterable, Unpack
from os import environ
from json import dumps
from logging import getLogger
from datetime import datetime
from numbers import Number
from re import search

from requests import Session
from secret_type import secret, Secret

from .api import post, Endpoint, sign, request, encode, decode, VERSION
from .exceptions import exception_factory, is_exception, LiqPayException
from .util import to_milliseconds, is_sandbox, verify_url

if TYPE_CHECKING:
    from .types import CallbackDict, RequestParamsDict
    from .types.post import PostParams


__all__ = ["Client"]


logger = getLogger(__name__)


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

    session: Session

    _public_key: str
    _private_key: Secret[bytes]

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        session: Session = None,
    ):
        self.update_keys(public_key, private_key)
        self.session = Session() if session is None else session

    @property
    def public_key(self) -> str:
        """Public key used for requests."""
        return self._public_key

    @property
    def sandbox(self) -> bool:
        """Check if client use sandbox LiqPay API."""
        return is_sandbox(self._public_key)

    def update_keys(self, /, public_key: str | None, private_key: str | None) -> None:
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
        self.session.close()

    def __del__(self):
        self.session.close()

    def _callback(
        self, data: bytes, signature: bytes, *, verify: bool = True
    ) -> "CallbackDict":
        if verify:
            self.verify(data, signature)
        else:
            logger.warning("Skipping signature verification")

        return decode(data)

    def sign(self, data: bytes, /) -> bytes:
        """
        Sign data string with private key.

        See `liqpy.api.sign` for more information.
        """
        with self._private_key.dangerous_reveal() as pk:
            return sign(data, key=pk)

    def encode(
        self, /, action: str, **kwargs: Unpack["RequestParamsDict"]
    ) -> tuple[bytes, bytes]:
        """
        Encode parameters into data and signature strings.

        >>> data, signature = client.encode("status", order_id="a1a1a1a1")

        See `liqpy.api.encode` for more information.
        """
        data = encode(request(action, key=self._public_key, **kwargs))
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

    def request(
        self, action: str, params: "RequestParamsDict", **kwargs: Unpack["PostParams"]
    ) -> dict:
        """
        Make a Server-Server request to LiqPay API.
        """
        response = post(
            Endpoint.REQUEST,
            *self.encode(action, **params),
            session=self.session,
            allow_redirects=False,
            stream=False,
            **kwargs,
        )

        if not response.headers.get("Content-Type", "").startswith("application/json"):
            raise LiqPayException(response=response)

        result: dict = response.json()

        if is_exception(action, result.pop("result", ""), result.get("status")):
            raise exception_factory(
                code=result.pop("err_code", None),
                description=result.pop("err_description", None),
                response=response,
                details=result,
            )

        return result

    def checkout(
        self,
        /,
        action: Literal["auth", "pay", "hold", "subscribe", "paydonate"],
        **kwargs: Unpack["RequestParamsDict"],
    ) -> str:
        """
        Make a Client-Server checkout request to LiqPay API.

        `kwargs` are passed to `requests.Session.post` method.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/checkout/doc)
        """
        assert action in (
            "auth",
            "pay",
            "hold",
            "subscribe",
            "paydonate",
        ), "Invalid action. Must be one of: auth, pay, hold, subscribe, paydonate"

        response = post(
            Endpoint.CHECKOUT, *self.encode(action, **kwargs), session=self.session
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
                details=result,
            )

        return next.url

    def reports(
        self,
        /,
        date_from: Union[datetime, str, Number],
        date_to: Union[datetime, str, Number],
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

        kwargs = {
            "date_from": to_milliseconds(date_from),
            "date_to": to_milliseconds(date_to),
        }

        if format is not None:
            kwargs["resp_format"] = format

        response = self._post_request(*self.encode("reports", **kwargs))

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
        kwargs = {}
        if payment_id is not None:
            kwargs["payment_id"] = payment_id

        if language is not None:
            kwargs["language"] = language

        self.request("receipt", order_id=order_id, email=email, **kwargs)

    def status(self, order_id: str, /) -> dict:
        """
        Get the status of a payment.

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/status/doc)
        """
        return self.request("status", order_id=order_id)

    def callback(self, /, data: str, signature: str, *, verify: bool = True):
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
        result = self._callback(data, signature, verify=verify)
        version = result.get("version")

        if version != VERSION:
            logger.warning("Callback version mismatch: %s != %s", version, VERSION)

        return result
