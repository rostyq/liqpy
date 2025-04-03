from typing import TYPE_CHECKING, Any, AnyStr, Optional, Unpack

from enum import Enum
from uuid import UUID

from urllib.parse import urljoin, urlencode
from base64 import b64encode, b64decode
from hashlib import sha1

from datetime import datetime

from httpx import (
    Client,
    AsyncClient,
    Response,
    USE_CLIENT_DEFAULT,
    __version__ as httpx_version,
)

from liqpy import __version__ as liqpy_version
from liqpy.constants import URL, VERSION

from .encoder import Encoder, JSONEncoder, SEPARATORS
from .decoder import Decoder, JSONDecoder
from .preprocess import Preprocessor, BasePreprocessor
from .validation import Validator, BaseValidator
from .exceptions import exception

if TYPE_CHECKING:
    from httpx._types import TimeoutTypes, RequestExtensions

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
    "post",
    "post_async",
    "sign",
    "encode",
    "decode",
    "request",
]


class Endpoint(Enum):
    """LiqPay API endpoints"""

    REQUEST: str = "/api/request"
    CHECKOUT: str = f"/api/{VERSION}/checkout"

    def url(self) -> str:
        """Return full URL for the endpoint"""
        return urljoin(URL, self.value)


def is_sandbox(key: str, /) -> bool:
    """Check if the key is a sandbox key"""
    return key.startswith("sandbox_")


_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": f"httpx/{httpx_version} {__package__}/{liqpy_version}",
}


def post(
    endpoint: Endpoint,
    /,
    data: AnyStr,
    signature: AnyStr,
    *,
    client: Client,
    timeout: Optional["TimeoutTypes"] = None,
    extensions: Optional["RequestExtensions"] = None,
) -> "Response":
    """
    Send POST request to LiqPay API

    See [Rules for the formation of a request for payment](https://www.liqpay.ua/en/documentation/data_signature).

    Arguments
    ---------
    - `endpoint` -- API endpoint to send request to (see `liqpy.Endpoint`)
    - `data` -- base64 encoded JSON data to send
    - `signature` -- LiqPay signature for the data
    - `session` -- `httpx.Client` instance to use

    Returns
    -------
    - `httpx.Response` instance

    Example
    -------
    >>> from httpx import Client
    >>> from liqpy.api import encode, sign, request, Endpoint
    >>> data = encode({"action": "status", "version": 3})
    >>> signature = sign(data, key=b"a4825234f4bae72a0be04eafe9e8e2bada209255")
    >>> with Client() as client:  # doctest: +SKIP
    ...     response = request(Endpoint.REQUEST, data, signature, client=client) # doctest: +SKIP
    ...     result = response.json() # doctest: +SKIP
    """
    return client.request(
        "POST",
        endpoint.url(),
        content=urlencode({"data": data, "signature": signature}).encode(),
        headers=_HEADERS,
        auth=None,
        timeout=USE_CLIENT_DEFAULT if timeout is None else timeout,
        follow_redirects=False,
        extensions=extensions,
    )


async def post_async(
    endpoint: Endpoint,
    /,
    data: AnyStr,
    signature: AnyStr,
    *,
    client: AsyncClient,
    timeout: Optional["TimeoutTypes"] = None,
    extensions: Optional["RequestExtensions"] = None,
) -> "Response":
    """
    Send POST request to LiqPay API asynchronously.

    See [Rules for the formation of a request for payment](https://www.liqpay.ua/en/documentation/data_signature).

    Arguments
    ---------
    - `endpoint` -- API endpoint to send request to (see `liqpy.Endpoint`)
    - `data` -- base64 encoded JSON data to send
    - `signature` -- LiqPay signature for the data
    - `client` -- `httpx.AsyncClient` instance to use

    Returns
    -------
    - `httpx.Response` instance

    Example
    -------
    >>> from httpx import AsyncClient
    >>> from liqpy.api import encode, sign, post_async, Endpoint
    >>> data = encode({"action": "status", "version": 3})
    >>> signature = sign(data, key=b"a4825234f4bae72a0be04eafe9e8e2bada209255")
    >>> async with AsyncClient() as client:  # doctest: +SKIP
    ...     response = await post_async(Endpoint.REQUEST, data, signature, client=client) # doctest: +SKIP
    ...     result = response.json() # doctest: +SKIP
    """
    return await client.request(
        "POST",
        endpoint.url(),
        content=urlencode({"data": data, "signature": signature}).encode(),
        headers=_HEADERS,
        auth=None,
        timeout=USE_CLIENT_DEFAULT if timeout is None else timeout,
        follow_redirects=False,
        extensions=extensions,
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
