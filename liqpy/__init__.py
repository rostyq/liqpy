from hashlib import sha1
from base64 import b64encode
from json import dumps
from os import environ

from requests import Session
from secret_type import secret, Secret

from .constants import VERSION, REQUEST_URL
from .exceptions import LiqPayException


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
        return f"{self.__class__.__name__}(public_key=\"{self.public_key}\")"

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

    def _prepare_params(self, /, **kwargs) -> dict:
        return kwargs | {"public_key": self.public_key, "version": VERSION}

    def _to_dict(self, /, data: str, signature: str) -> dict:
        return {"data": data, "signature": signature}

    def encode(self, /, **kwargs) -> tuple[str, str]:
        """Encode parameters into data and signature strings."""
        payload = dumps(self._prepare_params(**kwargs))
        data = self._encode_data(payload)
        signature = self._encode_signature(data)

        return data, signature

    def _request(self, /, data: str, signature: str) -> dict:
        data = self._to_dict(data, signature)
        response = self.session.post(REQUEST_URL, data=data)
        response.raise_for_status()
        return response.json()

    def request(self, /, **kwargs) -> dict:
        """Make a Server-Server request to LiqPay API."""
        data, signature = self.encode(**kwargs)
        data: dict[str] = self._request(data, signature)

        action = kwargs.get("action")
        result, status = data.pop("result"), data.get("status")

        if result == "error" or status in ["error", "failure"]:
            if action != "status":
                code = data.pop("err_code", "unknown")
                description = data.pop("err_description", "unknown error")
                raise LiqPayException(code, description, **data)

        return data
