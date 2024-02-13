from typing import TYPE_CHECKING
from datetime import datetime
from re import fullmatch
from numbers import Number
from uuid import UUID
from urllib.parse import urlparse

from liqpy.models.request import DetailAddenda, SplitRule, FiscalItem, FiscalInfo

if TYPE_CHECKING:
    from liqpy.types.request import (
        DetailAddendaDict,
        SplitRuleDict,
        FiscalItemDict,
        FiscalInfoDict,
        LiqpayRequestDict,
    )


def noop(value, /, **kwargs):
    pass


def number(value, /):
    assert isinstance(value, Number), f"value must be a number"


def gt(value, /, *, threshold: Number):
    number(value)
    assert value > threshold, f"value must be greater than {threshold}"


def string(value, /, *, max_len: int | None = None):
    assert isinstance(value, str), f"value must be a string"
    if max_len is not None:
        assert len(value) <= max_len, f"string must be less than {max_len} characters"


def url(value, /, *, max_len: int | None = None):
    string(value, max_len=max_len)
    result = urlparse(value or "")
    assert result.scheme in (
        "http",
        "https",
    ), "Invalid URL scheme. Must be http or https."
    assert result.netloc != "", f"Must be a valid URL."


def to_dict(o: dict[str], cls: type) -> dict:
    if isinstance(o, cls):
        return o.__dict__
    elif isinstance(o, dict):
        return o
    else:
        raise AssertionError(f"Invalid object type. Must be {cls} or dict.")


def check_required(params: dict[str], keys: set[str]):
    missing = keys - params.keys()
    assert not missing, f"Missing required parameters: {missing}"


class BaseValidator:
    """Base class for LiqPay API request validator"""

    def __call__(self, o: "LiqpayRequestDict", /, **kwargs):
        for key, value in o.items():
            try:
                getattr(self, key, noop)(value, **kwargs.get(key, {}))
            except AssertionError as e:
                raise AssertionError(f"Invalid {key} parameter.") from e
            except Exception as e:
                raise Exception(f"Failed to verify {key} parameter.") from e


class Validator(BaseValidator):
    """LiqPay API request validator"""

    def version(self, value, /, **kwargs):
        assert isinstance(value, int), f"version must be an integer"
        assert value > 0, f"version must be greater than 0"

    def public_key(self, value, /, **kwargs):
        string(value)

    def action(self, value, /, **kwargs):
        string(value)

    def order_id(self, value, /, **kwargs):
        if not isinstance(value, UUID):
            assert isinstance(value, str), "order_id must be a string or UUID"
            assert len(value) <= 255, "order_id must be less than 255 characters"

    def description(self, value, /, **kwargs):
        # NOTE: API allows to request up to 49 720 characters,
        # but cuts to 2048 characters long
        string(value, max_len=2048)

    def amount(self, value, /, **kwargs):
        gt(value, threshold=0)

    def currency(self, value, /, **kwargs):
        assert value in ("USD", "UAH"), "currency must be USD or UAH"

    def expired_date(self, value, /, **kwargs):
        assert isinstance(value, datetime), "expired_date must be a datetime"

    def date_from(self, value, /, **kwargs):
        assert isinstance(value, int), "date_from must be a int"

    def date_to(self, value, /, **kwargs):
        assert isinstance(value, int), "date_to must be a int"

    def resp_format(self, value, /, **kwargs):
        assert value in (
            "json",
            "csv",
            "xml",
        ), "format must be json, csv or xml"

    def phone(self, value, /, **kwargs):
        assert fullmatch(
            r"\+?380\d{9}", value
        ), "phone must be in format +380XXXXXXXXX or 380XXXXXXXXX"

    def sender_phone(self, value, /, **kwargs):
        self.phone(value)

    def info(self, value, /, **kwargs):
        string(value)

    def language(self, value, /, **kwargs):
        assert value in ("uk", "en"), "language must be uk or en"

    def card_number(self, value, /, **kwargs):
        assert fullmatch(r"\d{16}", value), f"card must be 16 digits long"

    def card_cvv(self, value, /, **kwargs):
        assert fullmatch(r"\d{3}", value), f"cvv must be 3 digits long"

    def card_exp_year(self, value, /, **kwargs):
        assert fullmatch(
            r"(\d{2})?\d{2}", value
        ), f"exp_year must be 2 or 4 digits long"

    def card_exp_month(self, value, /, **kwargs):
        assert fullmatch(
            r"(0[1-9])|(1[0-2])", value
        ), f"exp_month must be 2 digits long and between 01 and 12"

    def subscribe(self, value, /, **kwargs):
        assert value == 1, "subscribe must be 1"

    def subscribe_periodicity(self, value, /, **kwargs):
        assert value in ("month", "year"), "subscribe_periodicity must be month or year"

    def subscribe_date_start(self, value, /, **kwargs):
        assert isinstance(value, datetime), "subscribe_date_start must be a datetime"

    def paytype(self, value, /, **kwargs):
        assert value in (
            "apay",
            "gpay",
            "apay_tavv",
            "gpay_tavv",
            "tavv",
        ), "paytype must be one of: apay, gpay, apay_tavv, gpay_tavv, tavv"

    def payoption(self, value, /, **kwargs):
        assert value in (
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

    def paytypes(self, value, /, **kwargs):
        if isinstance(value, list):
            for i, item in enumerate(value):
                try:
                    self.payoption(item, **kwargs)
                except AssertionError as e:
                    raise AssertionError(f"Invalid paytypes element {i}.") from e

    def customer(self, value, /, **kwargs):
        string(value, max_len=100)

    def customer_user_id(self, value, /, **kwargs):
        string(value)

    def reccuringbytoken(self, value, /, **kwargs):
        assert value == "1", "reccuringbytoken must be 1"

    def dae(self, value, /, **kwargs):
        value: "DetailAddendaDict" = to_dict(value, DetailAddenda)

        try:
            string(value["air_line"], max_len=4)
            string(value["ticket_number"], max_len=15)
            string(value["passenger_name"], max_len=29)
            string(value["flight_number"], max_len=5)
            string(value["origin_city"], max_len=5)
            string(value["destination_city"], max_len=5)
        except AssertionError as e:
            raise AssertionError("Invalid dae object.") from e

    def split_rule(self, value, /, **kwargs):
        value: "SplitRuleDict" = to_dict(value, SplitRule)

        string(value["public_key"])
        gt(value["amount"], threshold=0)
        assert value["commission_payer"] in (
            "sender",
            "receiver",
        ), "commission_payer must be sender or receiver"
        url(value["server_url"])

    def split_rules(self, value, /, **kwargs):
        assert isinstance(value, list), "split_rules must be a list"
        for i, rule in enumerate(value):
            try:
                self.split_rule(rule, **kwargs)
            except AssertionError as e:
                raise AssertionError(
                    f"Invalid split_rule[{i}] object in split_rules."
                ) from e

    def fiscal_data(self, value, /, **kwargs):
        value: "FiscalItemDict" = to_dict(value, FiscalItem)

        assert isinstance(value["id"], int), "Invalid id. Must be an integer."

        for value in (value["amount"], value["cost"], value["price"]):
            gt(value, threshold=0)

    def rro_info(self, value, /, **kwargs):
        value: "FiscalInfoDict" = to_dict(value, FiscalInfo)

        assert isinstance(value["items"], list), "items in rro_info must be a list"
        assert isinstance(
            value["delivery_emails"], list
        ), "delivery_emails in rro_info must be a list"

        for i, item in enumerate(value["items"]):
            try:
                self.fiscal_data(item, **kwargs)
            except AssertionError as e:
                raise AssertionError(f"Invalid items[{i}] object in rro_info.") from e

        for i, email in enumerate(value.delivery_emails):
            try:
                string(email)
            except AssertionError as e:
                raise AssertionError(
                    f"Invalid delivery_emails[{i}] object in rro_info."
                ) from e

    def verifycode(self, value, /, **kwargs):
        assert value == "Y", "verifycode must be Y"

    def server_url(self, value, /, **kwargs):
        url(value, max_len=510)

    def result_url(self, value, /, **kwargs):
        # string(value, max_len=510)
        url(value, max_len=510)

    def product_url(self, value, /, **kwargs):
        url(value, max_len=2000)

    def product_description(self, value, /, **kwargs):
        string(value, max_len=500)

    def product_name(self, value, /, **kwargs):
        string(value, max_len=100)

    def product_category(self, value, /, **kwargs):
        string(value, max_len=25)

    def product_name(self, value, /, **kwargs):
        string(value, max_len=100)

    def product_category(self, value, /, **kwargs):
        string(value, max_len=25)
