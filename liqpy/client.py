from typing import Optional, Literal, Union, TYPE_CHECKING
from hashlib import sha1
from base64 import b64encode, b64decode
from os import environ
from json import dumps, loads
from logging import getLogger
from datetime import datetime
from numbers import Number
from re import search

from requests import Session, Response
from secret_type import secret, Secret

from .constants import VERSION, REQUEST_URL, CHECKOUT_URL
from .exceptions import exception_factory, is_exception, LiqPayException
from .util import to_milliseconds, to_dict, is_sandbox

if TYPE_CHECKING:
    from .types import CallbackDict, Language, Format


__all__ = ["Client"]


logger = getLogger(__name__)


class Client:
    """
    [LiqPay API](https://www.liqpay.ua/en/documentation/api/home) authorized client.

    Intialize by setting environment variables
    `LIQPAY_PUBLIC_KEY` and `LIQPAY_PRIVATE_KEY`:
    >>> from liqpy.client import Client
    >>> client = Client()

    Or pass them as arguments:
    >>> client = Client(public_key="...", private_key="...")

    For using custom session object pass it as an keyword argument:
    >>> from requests import Session
    >>> with Session() as session:
    >>>     client = Client(session=session)

    Client implements context manager interface same as `requests.Session`:
    >>> with Client() as client:
    >>>     pass
    >>> # client.session is closed
    """

    session: Session

    _public_key: str
    _private_key: Secret[str]

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
        return self._public_key

    @property
    def sandbox(self) -> bool:
        return is_sandbox(self._public_key)

    def update_keys(self, /, public_key: str | None, private_key: str | None) -> None:
        if public_key is None:
            public_key = environ["LIQPAY_PUBLIC_KEY"]
        else:
            public_key = str(public_key)

        if private_key is None:
            private_key = environ["LIQPAY_PRIVATE_KEY"]
        else:
            private_key = str(private_key)

        sandbox = is_sandbox(public_key)
        if sandbox != is_sandbox(private_key):
            raise ValueError("Public and private keys must be both sandbox or both not")

        self._public_key = public_key
        self._private_key = secret(private_key)

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

    def _prepare(self, /, action: str, **kwargs) -> dict:
        return {
            **kwargs,
            "public_key": self._public_key,
            "version": VERSION,
            "action": str(action),
        }

    def _post(self, url: str, /, data: str, signature: str, **kwargs) -> "Response":
        response = self.session.post(url, data=to_dict(data, signature), **kwargs)
        response.raise_for_status()
        return response

    def _post_request(
        self, /, data: str, signature: str, *, stream: bool = False
    ) -> "Response":
        return self._post(REQUEST_URL, data, signature, stream=stream)

    def _post_checkout(
        self, /, data: str, signature: str, *, redirect: bool = False
    ) -> "Response":
        return self._post(CHECKOUT_URL, data, signature, allow_redirects=redirect)

    def _callback(
        self, data: str, signature: str, *, verify: bool = True
    ) -> "CallbackDict":
        if verify:
            self.verify(data, signature)
        else:
            logger.warning("Skipping signature verification")

        return loads(b64decode(data, validate=True))

    def sign(self, data: str, /) -> str:
        """Sign data string with private key."""
        with self._private_key.dangerous_reveal() as pk:
            payload = f"{pk}{data}{pk}".encode()
            return b64encode(sha1(payload).digest()).decode()

    def encode(self, /, action: str, **kwargs) -> tuple[str, str]:
        """Encode parameters into data and signature strings."""
        data = dumps(self._prepare(action, **kwargs))
        data = b64encode(data.encode()).decode()
        signature = self.sign(data)

        return data, signature

    def is_valid(self, /, data: str, signature: str) -> bool:
        """Check if the signature is valid."""
        return self.sign(data) == signature

    def verify(self, /, data: str, signature: str) -> None:
        """Verify if the signature is valid. Raise an `AssertionError` if not."""
        assert self.is_valid(data, signature), "Invalid signature"

    def request(self, action: str, **kwargs) -> dict:
        """
        Make a Server-Server request to LiqPay API.
        """
        response = self._post_request(*self.encode(action, **kwargs))

        if not response.headers.get("Content-Type", "").startswith("application/json"):
            raise LiqPayException(response=response)

        result: dict = response.json()

        if is_exception(action, result.pop("result"), result.get("status")):
            raise exception_factory(
                code=result.pop("err_code"),
                description=result.pop("err_description"),
                response=response,
                details=result,
            )

        return result

    def checkout(self, /, action: str, **kwargs) -> str:
        """
        Make a Client-Server checkout request to LiqPay API.
        """
        response = self._post_checkout(*self.encode(action, **kwargs), redirect=False)

        next = response.next

        if next is not None:
            return next.url
        else:
            raise LiqPayException(response=response)

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
        >>> from uuid import uuid4
        >>> from liqpy.client import Client
        >>> client = Client()
        >>> # get data and signature from webhook request body
        >>> order_id = str(uuid4())
        >>> data, signature = client.encode(
        >>>     action="pay",
        >>>     amount=1,
        >>>     order_id=order_id,
        >>>     description="Test Encoding",
        >>>     currency="USD",
        >>> )
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
