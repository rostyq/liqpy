from typing import TYPE_CHECKING, Any, AnyStr, Optional, Unpack

from enum import Enum

from urllib.parse import urljoin
from base64 import b64encode, b64decode
from hashlib import sha1
from json import loads, JSONEncoder

from datetime import datetime, UTC

from liqpy.constants import URL, VERSION

from .encoder import Encoder, JSONEncoder
from .decoder import Decoder, JSONDecoder
from .preprocess import Preprocessor, BasePreprocessor
from .validation import Validator, BaseValidator
from .exceptions import exception

if TYPE_CHECKING:
    from requests import Session, Response

    from liqpy.types import LiqpayRequestDict
    from liqpy.types.action import Action
    from liqpy.types.post import Hooks, Proxies, Timeout, Verify, Cert


__all__ = ("Endpoint", "post", "sign", "encode", "decode", "request")


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


def post(
    endpoint: Endpoint,
    /,
    data: AnyStr,
    signature: AnyStr,
    *,
    session: "Session",
    stream: bool = False,
    allow_redirects: bool = False,
    proxies: Optional["Proxies"] = None,
    timeout: Optional["Timeout"] = None,
    hooks: Optional["Hooks"] = None,
    verify: Optional["Verify"] = None,
    cert: Optional["Cert"] = None,
) -> "Response":
    """
    Send POST request to LiqPay API

    See [Rules for the formation of a request for payment](https://www.liqpay.ua/en/documentation/data_signature).

    Arguments
    ---------
    - `endpoint` -- API endpoint to send request to (see `liqpy.Endpoint`)
    - `data` -- base64 encoded JSON data to send
    - `signature` -- LiqPay signature for the data
    - `session` -- `requests.Session` instance to use
    - `stream` -- whether to stream the response
    - `allow_redirects` -- whether to follow redirects
    - `proxies` -- proxies to use
    (see [Requests Proxies](https://docs.python-requests.org/en/stable/user/advanced/#proxies))
    - `timeout` -- timeout for the request
    - `hooks` -- hooks for the request
    (see [Requests Event Hooks](https://docs.python-requests.org/en/stable/user/advanced/#event-hooks))
    - `verify` -- whether to verify SSL certificate
    (see [Request SSL Cert Verification](https://requests.readthedocs.io/en/stable/user/advanced/#ssl-cert-verification))
    - `cert` -- client certificate to use
    (see [Request Client Side Certificates](https://requests.readthedocs.io/en/stable/user/advanced/#client-side-certificates))

    Returns
    -------
    - `requests.Response` instance

    Example
    -------
    >>> from requests import Session
    >>> from liqpy.api import encode, sign, request, Endpoint
    >>> data = encode({"action": "status", "version": 3})
    >>> signature = sign(data, key=b"a4825234f4bae72a0be04eafe9e8e2bada209255")
    >>> with Session() as session:  # doctest: +SKIP
    ...     response = request(Endpoint.REQUEST, data, signature, session=session) # doctest: +SKIP
    ...     result = response.json() # doctest: +SKIP
    """
    # print(data)
    response = session.request(
        method="POST",
        url=endpoint.url(),
        data={"data": data, "signature": signature},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        json=None,
        params=None,
        cookies=None,
        files=None,
        auth=None,
        proxies=proxies,
        timeout=timeout,
        hooks=hooks,
        allow_redirects=allow_redirects,
        stream=stream,
        verify=verify,
        cert=cert,
    )
    response.raise_for_status()
    return response


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
    validator: Optional[BaseValidator] = None,
    encoder: Optional[JSONEncoder] = None,
    preprocessor: Optional[BasePreprocessor] = None,
) -> bytes:
    """
    Encode parameters into base64 encoded JSON

    >>> encode({"action": "status", "version": 3})
    b'eyJhY3Rpb24iOiAic3RhdHVzIiwgInZlcnNpb24iOiAzfQ=='
    """
    if filter_none:
        params = {key: value for key, value in params.items() if value is not None}

    if encoder is None:
        encoder = Encoder()

    if preprocessor is None:
        preprocessor = Preprocessor()

    preprocessor(params, encoder=encoder)

    if validator is None:
        validator = Validator()

    validator(params)

    return b64encode(encoder.encode(params).encode())


def decode(data: bytes, /, decoder: Optional[JSONDecoder] = None) -> dict[str, Any]:
    """Decode base64 encoded JSON"""
    if decoder is None:
        decoder = Decoder()

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

    match action:
        case "subscribe":
            subscribe_date_start = params.get("subscribe_date_start")

            if subscribe_date_start is None:
                subscribe_date_start = datetime.now(UTC)
            
            assert "subscribe_periodicity" in params, "subscribe_periodicity is required"

            params.update(
                subscribe=True,
                subscribe_date_start=subscribe_date_start,
            )
        
        case "letter_of_credit":
            params["letter_of_credit"] = True

    return params
