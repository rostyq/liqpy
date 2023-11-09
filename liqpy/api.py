from typing import TYPE_CHECKING, Any, AnyStr, Optional, Unpack

from functools import singledispatchmethod
from enum import Enum
from dataclasses import asdict

from urllib.parse import urljoin
from base64 import b64encode, b64decode
from hashlib import sha1
from json import loads, JSONEncoder

from uuid import UUID
from decimal import Decimal
from datetime import date, datetime, UTC

from .data import FiscalItem, DetailAddenda, SplitRule
from .preprocess import Preprocessor, BasePreprocessor
from .validation import Validator, BaseValidator

if TYPE_CHECKING:
    from requests import Session, Response

    from .types import LiqpayRequestDict
    from .types.action import Action
    from .types.post import Hooks, Proxies, Timeout, Verify, Cert


__all__ = ("Endpoint", "post", "sign", "encode", "decode", "request")

URL = "https://www.liqpay.ua"
VERSION = 3

SENDER_KEYS = {
    "sender_first_name",
    "sender_last_name",
    "sender_email",
    "sender_address",
    "sender_city",
    "sender_country_code",
    "sender_postal_code",
    "sender_shipping_state",
}

PRODUCT_KEYS = {
    "product_category",
    "product_description",
    "product_name",
    "product_url",
}


class Endpoint(Enum):
    REQUEST: str = "/api/request"
    CHECKOUT: str = f"/api/{VERSION}/checkout"

    def url(self) -> str:
        return urljoin(URL, self.value)


class LiqPayJSONEncoder(JSONEncoder):
    date_fmt = r"%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(
            skipkeys=False,
            ensure_ascii=True,
            check_circular=True,
            allow_nan=False,
            sort_keys=False,
            indent=None,
            separators=None,
            default=None,
        )

    @singledispatchmethod
    def default(self, o):
        return super().default(o)

    @default.register
    def _(self, o: Decimal) -> float:
        return round(float(o), 4)

    @default.register
    def _(self, o: datetime) -> str:
        return o.astimezone(UTC).strftime(self.date_fmt)

    @default.register
    def _(self, o: date) -> str:
        return o.strftime(self.date_fmt)

    @default.register
    def _(self, o: bytes) -> str:
        return o.decode("utf-8")

    @default.register
    def _(self, o: UUID) -> str:
        return str(o)

    @default.register
    def _(self, o: DetailAddenda) -> str:
        return b64encode(self.encode(o.to_dict()).encode()).decode()

    @default.register
    def _(self, o: SplitRule) -> dict:
        return asdict(o)

    @default.register
    def _(self, o: FiscalItem) -> dict:
        return asdict(o)


def is_sandbox(key: str, /) -> bool:
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
    Send POST request to LiqPay API.

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
    Sign data string with private key.

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
    Encode parameters into base64 encoded JSON.

    >>> encode({"action": "status", "version": 3})
    b'eyJhY3Rpb24iOiAic3RhdHVzIiwgInZlcnNpb24iOiAzfQ=='
    """
    if filter_none:
        params = {key: value for key, value in params.items() if value is not None}

    if encoder is None:
        encoder = LiqPayJSONEncoder()

    if preprocessor is None:
        preprocessor = Preprocessor()

    preprocessor(params, encoder=encoder)

    if validator is None:
        validator = Validator()

    validator(params)

    return b64encode(encoder.encode(params).encode())


def decode(data: bytes, /) -> dict[str, Any]:
    """Decode base64 encoded JSON."""
    return loads(b64decode(data))


def request(
    action: "Action",
    /,
    public_key: str,
    *,
    version: int = VERSION,
    **params: "Unpack[LiqpayRequestDict]",
) -> "LiqpayRequestDict":
    """
    Create data dictionary for LiqPay API request.

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
