from typing import TYPE_CHECKING, Any, AnyStr, Optional, Unpack

from enum import Enum
from uuid import UUID

from urllib.parse import urljoin, urlencode
from base64 import b64encode, b64decode
from hashlib import sha1

from datetime import datetime

from httpx import (
    Response,
    __version__ as _httpx_version,
    request as _httpx_request,
)
from httpx._config import DEFAULT_TIMEOUT_CONFIG

from liqpy import __version__ as _liqpy_version
from liqpy.constants import BASE_URL, VERSION, REQUEST_ENDPOINT, CHECKOUT_ENDPOINT

from .encoder import Encoder, JSONEncoder, SEPARATORS
from .decoder import Decoder, JSONDecoder
from .preprocess import Preprocessor, BasePreprocessor
from .validation import Validator, BaseValidator
from .exceptions import exception

if TYPE_CHECKING:
    from httpx._types import TimeoutTypes, ProxyTypes

    from liqpy.types import LiqpayRequestDict
    from liqpy.types.action import Action


__all__ = [
    "Encoder",
    "Decoder",
    "Preprocessor",
    "Validator",
    "exception",
    "Endpoint",
    "is_sandbox",
    "sign",
    "encode",
    "decode",
    "request",
    "payload",
]


class Endpoint(Enum):
    """LiqPay API endpoints"""

    REQUEST: str = REQUEST_ENDPOINT
    CHECKOUT: str = CHECKOUT_ENDPOINT

    def url(self) -> str:
        """Return full URL for the endpoint"""
        return urljoin(BASE_URL, self.value)


def is_sandbox(key: str, /) -> bool:
    """Check if the key is a sandbox key"""
    return key.startswith("sandbox_")


COMMON_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": f"httpx/{_httpx_version} {__package__}/{_liqpy_version}",
}


def payload(*, data: AnyStr, signature: AnyStr) -> bytes:
    return urlencode({"data": data, "signature": signature}).encode()


def post(
    endpoint: Endpoint,
    /,
    data: AnyStr,
    signature: AnyStr,
    *,
    proxy: Optional["ProxyTypes"] = None,
    timeout: "TimeoutTypes" = DEFAULT_TIMEOUT_CONFIG,
    trust_env: bool = True,
) -> "Response":
    """
    Send POST request to LiqPay API

    See [Rules for the formation of a request for payment](https://www.liqpay.ua/en/documentation/data_signature).

    Arguments
    ---------
    - `endpoint` -- API endpoint to send request to (see `liqpy.Endpoint`)
    - `data` -- base64 encoded JSON data to send
    - `signature` -- LiqPay signature for the data
    - `proxy` -- proxy settings (see `httpx.Proxy`)
    - `timeout` -- timeout settings (see `httpx.Timeout`)
    - `trust_env` -- enables or disables usage of environment variables for `httpx` configuration.

    Returns
    -------
    - `httpx.Response` instance

    Example
    -------
    >>> from liqpy.api import encode, sign, post, Endpoint
    >>> data = encode({"action": "status", "version": 3})
    >>> signature = sign(data, key=b"a4825234f4bae72a0be04eafe9e8e2bada209255")
    >>> response = post(Endpoint.REQUEST, data, signature)  # doctest: +SKIP
    >>> result = response.json() # doctest: +SKIP
    """
    return _httpx_request(
        "POST",
        endpoint.url(),
        content=payload(data=data, signature=signature),
        headers=COMMON_HEADERS,
        proxy=proxy,
        timeout=timeout,
        follow_redirects=False,
        trust_env=trust_env,
    )


def sign(data: bytes, /, key: bytes) -> bytes:
    """
    Sign data string with private key

    Algorithm:

    1. Concatenate the private key with the data string as `key + data + key`
    2. Calculate SHA1 hash of the concatenated string
    3. Encode the hash in base64

    >>> data = encode({"action": "status", "version": 3})
    >>> sign(data, key=b"a4825234f4bae72a0be04eafe9e8e2bada209255")
    b'qI0/snsDFB7MiYUxrqhBqX2420E='
    """
    return b64encode(sha1(key + data + key).digest())


def encode(
    params: "LiqpayRequestDict",
    /,
    *,
    filter_none: bool = True,
    encoder: Optional[JSONEncoder] = None,
    preprocessor: Optional[BasePreprocessor] = None,
    validator: Optional[BaseValidator] = None,
) -> bytes:
    """
    Encode parameters into base64 encoded JSON

    >>> encode({"action": "status", "version": 3})
    b'eyJhY3Rpb24iOiAic3RhdHVzIiwgInZlcnNpb24iOiAzfQ=='
    """
    if filter_none:
        params = {key: value for key, value in params.items() if value is not None}

    if encoder is None:
        encoder = JSONEncoder(separators=SEPARATORS)

    if preprocessor is not None:
        preprocessor(params, encoder=encoder)

    if validator is not None:
        validator(params)

    return b64encode(encoder.encode(params).encode())


def decode(data: bytes, /, decoder: Optional[JSONDecoder] = None) -> dict[str, Any]:
    """Decode base64 encoded JSON"""
    if decoder is None:
        decoder = JSONDecoder()

    return decoder.decode(b64decode(data).decode())


def request(
    action: "Action",
    /,
    public_key: str,
    *,
    version: int = VERSION,
    **params: "Unpack[LiqpayRequestDict]",
) -> "LiqpayRequestDict":
    """
    Create data dictionary for LiqPay API request

    >>> request("status", key="...", order_id="a1a1a1a1")
    {'action': 'status', 'public_key': '...', 'version': 3, 'order_id': 'a1a1a1a1'}
    """
    params.update(action=action, public_key=public_key, version=version)

    liqpay_id = params.pop("opid", None)
    if isinstance(liqpay_id, (str, UUID)):
        params.setdefault("order_id", liqpay_id)
    elif isinstance(liqpay_id, int):
        params.setdefault("payment_id", str(liqpay_id))

    match action:
        case "subscribe":
            assert (
                "subscribe_periodicity" in params
            ), "subscribe_periodicity is required"
            params["subscribe"] = True

            if params.get("subscribe_date_start") is None:
                params["subscribe_date_start"] = datetime.now()

        case "letter_of_credit":
            params["letter_of_credit"] = True

    return params
