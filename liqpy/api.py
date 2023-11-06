from typing import (
    TYPE_CHECKING,
    Any,
    AnyStr,
    Optional,
    Unpack,
)

from functools import singledispatchmethod
from enum import Enum

from urllib.parse import urljoin
from base64 import b64encode, b64decode
from hashlib import sha1
from json import dumps, loads, JSONEncoder
from re import fullmatch

from uuid import UUID
from decimal import Decimal
from datetime import date, datetime, UTC

from .util import DetailAddenda, verify_url, SplitRule, FiscalData, update_keys


if TYPE_CHECKING:
    from requests import Session, Response

    from .types import RequestParamsDict, RequestDict
    from .types.action import Action
    from .types.post import Hooks, Proxies, Timeout, Verify, Cert


__all__ = ("Endpoint", "post", "sign", "encode", "decode", "request")

URL = "https://www.liqpay.ua/api"
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
    REQUEST: str = "/request"
    CHECKOUT: str = f"/{VERSION}/checkout"

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
    def _(self, o: FiscalData) -> dict:
        return {
            "id": o.id,
            "amount": o.amount,
            "cost": o.cost,
            "price": o.price,
        }


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
        json=None,
        params=None,
        headers=None,
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


def encode(params: object, /) -> bytes:
    """
    Encode parameters into base64 encoded JSON.

    >>> encode({"action": "status", "version": 3})
    b'eyJhY3Rpb24iOiAic3RhdHVzIiwgInZlcnNpb24iOiAzfQ=='
    """
    s = dumps(
        obj=params,
        skipkeys=False,
        ensure_ascii=False,
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
    key: str,
    *,
    version: int = VERSION,
    **kwargs: Unpack["RequestParamsDict"],
) -> "RequestDict":
    """
    Create data dictionary for LiqPay API request.

    >>> data("status", key="...", order_id="a1a1a1a1")
    {'action': 'status', 'public_key': '...', 'version': 3, 'order_id': 'a1a1a1a1'}
    """
    result: "RequestParamsDict" = {}
    result.update(action=action, public_key=key, version=version)

    if action == "reports":
        date_from = kwargs.pop("date_from")
        assert isinstance(date_from, datetime)

        date_to = kwargs.pop("date_to")
        assert isinstance(date_to, datetime)

        result.update(date_from=date_from, date_to=date_to)

        resp_format = kwargs.pop("resp_format", None)
        if resp_format is not None:
            assert resp_format in (
                "json",
                "json",
                "xml",
            ), "format must be json, json or xml"
            result["resp_format"] = resp_format

        return result

    if "order_id" in kwargs:
        order_id = kwargs.pop("order_id")

        if not isinstance(order_id, UUID):
            assert len(order_id) <= 255, "order_id must be less than 255 characters"

        result["order_id"] = order_id

    if action in ("status", "invoice_cancel", "unsubscribe", "refund"):
        return result

    if "info" in kwargs:
        info = kwargs.pop("info")
        assert isinstance(info, str)
        result["info"] = info

    if action == "ticket":
        email = kwargs.pop("email")
        assert isinstance(email, str), "email must be a string"
        result["email"] = email

    if action == "data":
        return result

    if not kwargs.keys().isdisjoint({"amount", "currency"}):
        amount = Decimal(kwargs.pop("amount"))
        currency = kwargs.pop("currency")
        assert len(currency) == 3, "currency must be 3 characters long"
        assert currency in ("USD", "EUR", "UAH"), "currency must be USD, EUR or UAH"
        result.update(amount=amount, currency=currency)

    if "description" in kwargs:
        description = kwargs.pop("description")
        # NOTE: API allows to request up to 49 720 characters, but cuts the result to 2048
        assert len(description) <= 2048, "description must be less than 2048 characters"

    if "card" in kwargs:
        card = kwargs.pop("card")
        assert isinstance(card, str)
        assert len(card) == 14, "card must be 14 characters long"
        result["card"] = card

        card_exp_month = kwargs.pop("card_exp_month", None)
        if card_exp_month is not None:
            assert isinstance(card_exp_month, str)
            assert len(card_exp_month) == 2, "card_exp_month must be 2 characters long"
            assert card_exp_month.isdigit(), "card_exp_month must be a number"
            assert (
                1 <= int(card_exp_month) <= 12
            ), "card_exp_month must be between 1 and 12"
            result["card_exp_month"] = card_exp_month

        card_exp_year = kwargs.pop("card_exp_year")
        if card_exp_year is not None:
            assert isinstance(card_exp_year, str)
            assert len(card_exp_year) == 2, "card_exp_year must be 2 characters long"
            assert card_exp_year.isdigit(), "card_exp_year must be a number"
            assert (
                0 <= int(card_exp_year) <= 99
            ), "card_exp_year must be between 0 and 99"
            result["card_exp_year"] = card_exp_year

        card_cvv = kwargs.pop("card_cvv")
        if card_cvv is not None:
            assert isinstance(card_cvv, str)
            assert len(card_cvv) == 3, "card_cvv must be 3 characters long"
            assert card_cvv.isdigit(), "card_cvv must be a number"
            result["card_cvv"] = card_cvv

    if "expired_date" in kwargs:
        expired_date = kwargs.pop("expired_date")

        if isinstance(expired_date, str):
            expired_date = datetime.strptime(expired_date, "%Y-%m-%d %H:%M:%S")
        else:
            assert isinstance(expired_date, datetime)
        result["expired_date"] = expired_date

    if "language" in kwargs:
        language = kwargs.pop("language")
        assert language in ("uk", "en"), "language must be uk or en"

    if "phone" in kwargs:
        phone = kwargs.pop("phone")
        assert fullmatch(
            r"\+?380\d{9}", phone
        ), "phone must be in format +380XXXXXXXXX or 380XXXXXXXXX"
        result["phone"] = phone

    if "paytype" in kwargs:
        paytype = kwargs.pop("paytype")
        assert paytype in (
            "apay",
            "gpay",
            "apay_tavv",
            "gpay_tavv",
            "tavv",
        ), "paytype must be one of: apay, gpay, apay_tavv, gpay_tavv, tavv"

    if "paytypes" in kwargs:
        paytypes = kwargs.pop("paytypes")
        assert paytypes in (
            "apay",
            "gpay",
            "card",
            "liqpay",
            "moment_part",
            "paypart",
            "cash",
            "invoice",
            "qr",
        ), "paytypes must be one of: apay, gpay, card, liqpay, moment_part, paypart, cash, invoice, qr"

    if "server_url" in kwargs:
        server_url = kwargs.pop("server_url")
        verify_url(server_url)
        assert len(server_url) <= 510, "server_url must be less than 510 characters"

    if "server_url" in kwargs:
        server_url = kwargs.pop("server_url")
        verify_url(server_url)
        assert len(server_url) <= 510, "server_url must be less than 510 characters"

    if action == "auth" and "verifycode" in kwargs:
        if kwargs.pop("verifycode", False):
            result["verifycode"] = "Y"

    if "rro_info" in kwargs:
        rro_info = kwargs.pop("rro_info")
        assert isinstance(rro_info, dict)

        delivery_emails = rro_info.pop("delivery_emails", None)
        rro_info_items = rro_info.pop("items", None)

        rro_info = {}

        if delivery_emails is not None:
            assert isinstance(delivery_emails, list)
            for email in delivery_emails:
                assert isinstance(email, str)

            rro_info["delivery_emails"] = delivery_emails

        if rro_info_items is not None:
            assert isinstance(rro_info_items, list)

            rro_info["items"] = []
            for item in rro_info_items:
                if not isinstance(item, FiscalData):
                    item = FiscalData(**item)

                rro_info["items"].append(item)

        result["rro_info"] = rro_info

    if "split_rules" in kwargs:
        split_rules = kwargs.pop("split_rules")
        assert isinstance(split_rules, list), "split_rules must be a list"
        result["split_rules"] = [
            rule if isinstance(rule, SplitRule) else SplitRule(**rule)
            for rule in split_rules
        ]

    if not kwargs.keys().isdisjoint(SENDER_KEYS):
        update_keys(result, SENDER_KEYS, kwargs)

    if kwargs.keys().isdisjoint({"mpi_md", "mpi_pares"}):
        mpi_md = kwargs.pop("mpi_md", None)
        mpi_pares = kwargs.pop("mpi_pares", None)

        if mpi_md is not None:
            result["mpi_md"] = mpi_md

        if mpi_pares is not None:
            result["mpi_pares"] = mpi_pares

    if action == "letter_of_credit" or "letter_of_credit_date" in kwargs:
        letter_of_credit_date = kwargs.pop("letter_of_credit_date")
        assert isinstance(letter_of_credit_date, (datetime, str))
        result.update(letter_of_credit=1, letter_of_credit_date=letter_of_credit_date)

    if action == "subscribe":
        subscribe_date_start = kwargs.pop("subscribe_date_start", None)
        subscribe_periodicity = kwargs.pop("subscribe_periodicity", "month")

        if subscribe_date_start is None:
            subscribe_date_start = datetime.utcnow()

        assert subscribe_periodicity in (
            "month",
            "year",
        ), "Invalid subscribe periodicity. Must be one of: month, year"

        result.update(
            subscribe=1,
            subscribe_date_start=subscribe_date_start,
            subscribe_periodicity=subscribe_periodicity,
        )

    if "customer" in kwargs:
        customer = kwargs.pop("customer")
        assert isinstance(customer, str)
        assert len(customer) <= 100, "customer must be less than 100 characters"
        result["customer"] = customer

    if "reccuringbytoken" in kwargs:
        if kwargs.pop("reccuringbytoken", False):
            assert "server_url" in result, "server_url must be specified"
            result["reccuringbytoken"] = "1"

    if "customer_user_id" in kwargs:
        customer_user_id = kwargs.pop("customer_user_id")
        assert isinstance(customer_user_id, str)
        result["customer_user_id"] = customer_user_id

    if "dae" in kwargs:
        dae = kwargs.pop("dae")
        if not isinstance(dae, DetailAddenda):
            dae = DetailAddenda(**dae)
        result["dae"] = dae

    if not kwargs.keys().isdisjoint(PRODUCT_KEYS):
        product_category = kwargs.pop("product_category", None)
        if product_category is not None:
            assert (
                len(product_category) <= 25
            ), "Product category must be less than 25 characters"
            result["product_category"] = product_category

        product_description = kwargs.pop("product_description", None)
        if product_description is not None:
            assert (
                len(product_description) <= 500
            ), "Product description must be less than 500 characters"
            result["product_description"] = product_description

        product_name = kwargs.pop("product_name", None)
        if product_name is not None:
            assert (
                len(product_name) <= 100
            ), "Product name must be less than 100 characters"
            result["product_name"] = product_name

        product_url = kwargs.pop("product_url", None)
        if product_url is not None:
            verify_url(product_url)
            assert (
                len(product_url) <= 2000
            ), "Product URL must be less than 2000 characters"
            result["product_url"] = product_url

    result.update({k: v for k, v in kwargs.items() if v is not None})

    return result
