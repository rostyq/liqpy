from typing import TYPE_CHECKING, Any, AnyStr, Optional, Unpack

from functools import singledispatchmethod
from enum import Enum

from urllib.parse import urljoin
from base64 import b64encode, b64decode
from hashlib import sha1
from json import dumps, loads, JSONEncoder

from uuid import UUID
from decimal import Decimal
from datetime import date, datetime, UTC

from .data import FiscalItem, DetailAddenda, SplitRule
from .convert import to_datetime, to_milliseconds
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
        return encode(
            {
                "airLine": o.air_line,
                "ticketNumber": o.ticket_number,
                "passengerName": o.passenger_name,
                "flightNumber": o.flight_number,
                "originCity": o.origin_city,
                "destinationCity": o.destination_city,
                "departureDate": o.departure_date.strftime(r"%d%m%y"),
            }
        )

    @default.register
    def _(self, o: SplitRule) -> dict:
        return {
            "public_key": o.public_key,
            "amount": o.amount,
            "commission_payer": o.commission_payer,
            "server_url": o.server_url,
        }

    @default.register
    def _(self, o: FiscalItem) -> dict:
        return {
            "id": o.id,
            "amount": o.amount,
            "cost": o.cost,
            "price": o.price,
        }


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
    params: "LiqpayRequestDict", /, *, validator: type[BaseValidator] = Validator
) -> bytes:
    """
    Encode parameters into base64 encoded JSON.

    >>> encode({"action": "status", "version": 3})
    b'eyJhY3Rpb24iOiAic3RhdHVzIiwgInZlcnNpb24iOiAzfQ=='
    """
    validator()(params)
    
    dae = params.get("dae")
    if isinstance(dae, dict):
        params["dae"] = DetailAddenda(**dae)
    
    split_rules = params.get("split_rules")
    if split_rules is not None and isinstance(split_rules, list):
        params["split_rules"] = dumps(split_rules, cls=LiqPayJSONEncoder)

    paytypes = params.get("paytypes")
    if paytypes is not None and isinstance(paytypes, list):
        params["paytypes"] = ",".join(paytypes)

    s = dumps(
        obj=params,
        skipkeys=False,
        ensure_ascii=True,
        check_circular=True,
        indent=None,
        allow_nan=False,
        separators=None,
        sort_keys=False,
        cls=LiqPayJSONEncoder,
    )
    return b64encode(s.encode())


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
    params = {k: v for k, v in params.items() if v is not None}
    params.update(action=action, public_key=public_key, version=version)

    match action:
        case "reports":
            params.update(
                date_from=to_milliseconds(params["date_from"]),
                date_to=to_milliseconds(params["date_to"]),
            )
            return params

        case "status" | "invoice_cancel" | "unsubscribe" | "refund" | "data":
            return params

        case "auth":
            if params.get("verifycode", False):
                params["verifycode"] = "Y"

        case "subscribe":
            subscribe_date_start = params.get("subscribe_date_start")

            if subscribe_date_start is None:
                subscribe_date_start = datetime.now(UTC)

            params.update(
                subscribe=1,
                subscribe_date_start=to_datetime(subscribe_date_start),
            )

        case "letter_of_credit":
            params.update(
                letter_of_credit=1,
                letter_of_credit_date=to_datetime(params.get("letter_of_credit_date")),
            )

    if params.get("recurringbytoken", False):
        assert "server_url" in params, "server_url must be specified"
        params["reccuringbytoken"] = "1"

    return params
