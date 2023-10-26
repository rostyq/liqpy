from hashlib import sha1
from base64 import b64encode, b64decode
from json import dumps, loads
from os import environ

from requests import Session, Response
from secret_type import secret, Secret

from .constants import VERSION, REQUEST_URL, CHECKOUT_URL
from .exceptions import exception_factory, is_exception, LiqPayException


__all__ = ["LiqPay"]


class LiqPay:
    """LiqPay API client."""

    session: Session

    public_key: str
    private_key: Secret[str]

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

        if private_key is None:
            private_key = environ["LIQPAY_PRIVATE_KEY"]

        if session is None:
            session = Session()

        self.public_key = public_key
        self.private_key = secret(private_key)
        self.session = session

    def __repr__(self):
        return f'{self.__class__.__name__}(public_key="{self.public_key}")'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def __del__(self):
        self.session.close()

    def _encode_signature(self, data: str, /) -> str:
        with self.private_key.dangerous_reveal() as pk:
            payload = f"{pk}{data}{pk}".encode()
            return b64encode(sha1(payload).digest()).decode()

    def _encode_data(self, data: str, /) -> str:
        return b64encode(data.encode()).decode()
    
    def _decode_data(self, data: str, /) -> str:
        return b64decode(data.encode(), validate=True)

    def _prepare_params(self, params: dict, /) -> dict:
        return params | {"public_key": self.public_key, "version": VERSION}

    def _to_dict(self, /, data: str, signature: str) -> dict:
        return {"data": data, "signature": signature}

    def encode(self, /, **kwargs) -> tuple[str, str]:
        """Encode parameters into data and signature strings."""
        payload = dumps(self._prepare_params(kwargs))
        data = self._encode_data(payload)
        signature = self._encode_signature(data)

        return data, signature

    def is_valid(self, /, data: str, signature: str) -> bool:
        """Check if the signature is valid."""
        return self._encode_signature(data) == signature

    def verify(self, /, data: str, signature: str):
        """Verify if the signature is valid. Raise an exception if not."""
        assert self.is_valid(data, signature), "Invalid signature"

    def _request(self, /, data: str, signature: str) -> "Response":
        data = self._to_dict(data, signature)
        response = self.session.post(REQUEST_URL, data=data)
        response.raise_for_status()
        return response

    def _checkout(self, /, data: str, signature: str, *, redirect: bool = False) -> "Response":
        data = self._to_dict(data, signature)
        response = self.session.post(CHECKOUT_URL, data=data, allow_redirects=redirect)
        response.raise_for_status()
        return response

    def request(self, /, **kwargs) -> dict:
        """Make a Server-Server request to LiqPay API."""
        data, signature = self.encode(**kwargs)
        response = self._request(data, signature)
        data: dict[str] = response.json()

        action = kwargs.get("action")
        result, status = data.pop("result"), data.get("status")

        if is_exception(action, result, status):
            code = data.pop("err_code", "unknown")
            description = data.pop("err_description", "unknown error")
            raise exception_factory(code, description, response=response, **data)

        return data

    def checkout(self, /, **kwargs) -> str:
        """Make a Client-Server checkout request to LiqPay API."""
        response = self._checkout(*self.encode(**kwargs), redirect=False)

        next = response.next

        if next is not None:
            return next.url
        else:
            raise LiqPayException("unknown", "unknown error", response=response)

    def status(self, order_id: str, /) -> dict:
        """Get the status of a payment."""
        return self.request(action="status", order_id=order_id)

    def callback(self, data: str, signature: str) -> dict:
        """Verify and decode the callback data."""
        self.verify(data, signature)
        return loads(self._decode_data(data))
