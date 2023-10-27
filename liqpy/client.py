from typing import Optional, Literal
from hashlib import sha1
from base64 import b64encode, b64decode
from json import dumps, loads
from os import environ
from logging import getLogger
from datetime import datetime

from requests import Session, Response
from secret_type import secret, Secret

from .constants import VERSION, REQUEST_URL, CHECKOUT_URL
from .exceptions import exception_factory, is_exception, LiqPayException
from .types import CallbackDict, Language


__all__ = ["Client"]


logger = getLogger(__name__)


def encode(data: str, /) -> str:
    """Encode data string into base64 string."""
    return b64encode(data.encode()).decode()


def decode(data: str, /) -> str:
    """Decode base64 string into data."""
    return b64decode(data.encode(), validate=True)


def to_dict(data: str, signature: str, /) -> dict:
    """Convert data and signature into a dictionary."""
    return {"data": data, "signature": signature}


def to_milliseconds(dt: datetime, /) -> int:
    """Convert datetime into milliseconds."""
    return int(round(dt.timestamp() * 1000))


class Client:
    """
    [LiqPay API](https://www.liqpay.ua/en/documentation/api/home) authorized client.

    Intialize by setting environment variables
    `LIQPAY_PUBLIC_KEY` and `LIQPAY_PRIVATE_KEY`:
    >>> from liqpy import Client
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

    public_key: str
    private_key: Secret[str]

    sandbox: bool

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        session: Session = None,
    ):
        if public_key is None:
            public_key = environ["LIQPAY_PUBLIC_KEY"]
        else:
            public_key = str(public_key)

        if private_key is None:
            private_key = environ["LIQPAY_PRIVATE_KEY"]
        else:
            private_key = str(private_key)

        sandbox = public_key.startswith("sandbox_")

        if sandbox != private_key.startswith("sandbox_"):
            raise ValueError("Public and private keys must be both sandbox or both not")

        if sandbox:
            logger.warning("Using sandbox LiqPay API.")

        self.public_key = public_key
        self.private_key = secret(private_key)
        self.session = Session() if session is None else session
        self.sandbox = sandbox

    def __repr__(self):
        return f'{self.__class__.__name__}(public_key="{self.public_key}")'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def __del__(self):
        self.session.close()

    def _prepare(self, /, action: str, **kwargs) -> dict:
        params = {"public_key": self.public_key, "version": VERSION, "action": action}
        params.update(**kwargs)
        return params

    def _post(self, url: str, /, data: str, signature: str, **kwargs) -> "Response":
        response = self.session.post(url, data=to_dict(data, signature), **kwargs)
        response.raise_for_status()
        return response

    def _post_request(self, /, data: str, signature: str) -> "Response":
        return self._post(REQUEST_URL, data, signature)

    def _post_checkout(
        self, /, data: str, signature: str, *, redirect: bool = False
    ) -> "Response":
        return self._post(CHECKOUT_URL, data, signature, allow_redirects=redirect)

    def _callback(
        self, data: str, signature: str, *, verify: bool = True
    ) -> CallbackDict:
        if verify:
            self.verify(data, signature)
        else:
            logger.warning("Skipping signature verification")

        return loads(decode(data))

    def sign(self, data: str, /) -> str:
        """Sign data string with private key."""
        with self.private_key.dangerous_reveal() as pk:
            payload = f"{pk}{data}{pk}".encode()
            return b64encode(sha1(payload).digest()).decode()

    def encode(self, /, action: str, **kwargs) -> tuple[str, str]:
        """Encode parameters into data and signature strings."""
        data = encode(dumps(self._prepare(action, **kwargs)))
        signature = self.sign(data)

        return data, signature

    def is_valid(self, /, data: str, signature: str) -> bool:
        """Check if the signature is valid."""
        return self.sign(data) == signature

    def verify(self, /, data: str, signature: str):
        """Verify if the signature is valid. Raise an exception if not."""
        assert self.is_valid(data, signature), "Invalid signature"

    def request(self, action: str, **kwargs) -> dict:
        """
        Make a Server-Server request to LiqPay API.
        """
        response = self._post_request(*self.encode(action, **kwargs))
        result: dict = response.json()

        if is_exception(action, result.pop("result"), result.get("status")):
            code = result.pop("err_code", "unknown")
            description = result.pop("err_description", "unknown error")
            raise exception_factory(code, description, response=response, details=result)

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
            raise LiqPayException("unknown", "unknown error", response=response)

    def reports(
        self,
        /,
        date_from: datetime | str,
        date_to: datetime | str,
        format: Optional[Literal["json", "csv", "xml"]] = None,
    ) -> list[dict[str, str | int | float]] | str:
        """
        Get an archive of recieved payments.

        [Documentaion](https://www.liqpay.ua/en/documentation/api/information/reports/doc)
        """
        if isinstance(date_from, str):
            date_from = datetime.fromisoformat(date_from)

        if isinstance(date_to, str):
            date_to = datetime.fromisoformat(date_to)

        kwargs = {"date_from": to_milliseconds(date_from), "date_to": to_milliseconds(date_to)}

        if format is not None:
            kwargs["resp_format"] = format
        
        match format:
            case None | "json":
                return self.request("reports", **kwargs)["data"]
            case "csv" | "xml":
                return self._post_request(*self.encode("reports", **kwargs)).content.decode()
    
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
        language: Optional[Language] = None,
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

        [Documentation](https://www.liqpay.ua/en/documentation/api/callback)
        """
        result = self._callback(data, signature, verify=verify)
        version = result.get("version")

        if version != VERSION:
            logger.warning("Callback version mismatch: %s != %s", version, VERSION)

        return result