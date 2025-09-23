from typing import Any, Optional, Literal, TYPE_CHECKING, cast, Callable, Any
from functools import wraps
from datetime import datetime, timedelta, date, UTC
from decimal import Decimal
from collections.abc import Iterable, Mapping
from re import fullmatch
from uuid import UUID
from urllib.parse import urlparse
from ipaddress import IPv4Address

from liqpy.convert import noop, to_datetime, to_milliseconds
from liqpy.models.request import (
    DetailAddenda,
    SplitRule,
    SplitRules,
    FiscalInfo,
    PayOption,
    PayTypes,
)

if TYPE_CHECKING:
    from liqpy.types.request import LiqpayRequest


DEFAULT_NAME = "value"


def validate_url(value: str, /, name: str = "url") -> str:
    if (r := urlparse(value or "")).netloc == "":
        raise ValueError(f"{name} must be a valid URL.")
    elif r.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme for {name}. Must be http or https.")
    else:
        return value


def validate_string(value: Any, /, max_len: int, name: str = "value") -> str:
    if isinstance(value, str):
        if len(value) <= max_len:
            return value
        else:
            raise ValueError(f"{name} must be less than {max_len} characters")
    else:
        raise TypeError(f"{name} must be a string")


def validate_digits(value: Any, /, size: int, name: str = DEFAULT_NAME) -> str:
    if isinstance(value, str):
        if value.isdigit() and len(value) == size:
            return value
        else:
            raise ValueError(f"{name} must be {size} digits long")
    else:
        raise TypeError(f"{name} must be a string of {size} digits")


def validate_phone(value: Any, /, name: str = "phone") -> str:
    if isinstance(value, str):
        if fullmatch(r"\+?380\d{9}", value):
            return value
        else:
            raise ValueError(f"{name} must be in format +380XXXXXXXXX or 380XXXXXXXXX")
    else:
        raise TypeError(f"{name} must be a string representing a phone number")


def validate_amount(value, /, name: str = DEFAULT_NAME) -> Decimal:
    if isinstance(value, Decimal):
        if value > 0:
            return value
        else:
            raise ValueError(f"{name} must be positive")
    else:
        raise TypeError(f"{name} must be a decimal number")


def validate_datetype(fn: Callable[[Any, str], Any]):
    @wraps(fn)
    def wrapper(value, /, name: str):
        if isinstance(value, (datetime, timedelta, date, int, float, str, tuple)):
            try:
                return fn(value, name)
            except ValueError as e:
                raise ValueError(f"Invalid {name}. {e}") from e
        else:
            raise TypeError(
                f"{name} must be one of: datetime, timedelta, date, "
                "int (milliseconds), float (seconds), ISO8601 string, tuple (YEAR, MONTH, DAY)"
            )

    return wrapper


@validate_datetype
def validate_dateedge(value, /, name: str = "date") -> int:
    return to_milliseconds(value)


@validate_datetype
def validate_datetime(value, /, name: str = "datetime") -> datetime:
    return to_datetime(value)


def validate_one(value, /) -> Optional[Literal[1]]:
    return 1 if value else None


class LiqpayValidator:
    """LiqPay API request validator"""

    def __call__(self, request: "LiqpayRequest", /) -> "LiqpayRequest":
        errors: list[TypeError | ValueError] = []
        request = cast(
            "LiqpayRequest", {k: v for k, v in request.items() if v is not None}
        )

        # pre-process action-specific requirements
        match action := request.get("action"):
            case "subscribe":
                if "subscribe_periodicity" not in request:
                    errors.append(
                        ValueError(
                            "subscribe_periodicity is required for action 'subscribe'"
                        )
                    )
                request["subscribe"] = True

                if request.get("subscribe_date_start") is None:
                    request["subscribe_date_start"] = datetime.now(UTC)

            case "letter_of_credit":
                request["letter_of_credit"] = True

        # validate and transform parameters
        for key, value in request.items():
            try:
                value = getattr(self, key, noop)(value)
                if value is not None:
                    request[key] = value
            except* (ValueError, TypeError) as g:
                for e in g.exceptions:
                    if isinstance(e, ExceptionGroup):
                        errors.extend(
                            (
                                ee
                                for ee in e.exceptions
                                if isinstance(ee, (TypeError, ValueError))
                            )
                        )
                    else:
                        errors.append(e)

        # post-process action-specific requirements
        match action:
            case "reports":
                if (date_from := request.get("date_from")) is None:
                    errors.append(
                        ValueError("date_from is required for action 'reports'")
                    )
                if (date_to := request.get("date_to")) is None:
                    errors.append(
                        ValueError("date_to is required for action 'reports'")
                    )

                if date_from is not None and date_to is not None:
                    assert isinstance(date_from, int) and isinstance(date_to, int)
                    if date_from >= date_to:
                        errors.append(
                            ValueError("date_from must be earlier than date_to")
                        )

        # rename keys to match API requirements
        if (ds_trans_id := request.pop("ds_trans_id", None)) is not None:
            request["dsTransID"] = ds_trans_id  # type: ignore

        if len(errors) == 0:
            return request
        else:
            raise ExceptionGroup("Invalid request parameters.", errors)

    def version(self, value, /):
        if isinstance(value, int):
            if value > 0:
                return value
            else:
                raise ValueError("version must be greater than 0")
        else:
            raise TypeError("version must be an integer")

    def public_key(self, value, /):
        if isinstance(value, str):
            return value
        else:
            raise TypeError("public_key must be a string")

    def action(self, value, /):
        if isinstance(value, str):
            return value
        else:
            raise TypeError("action must be a string")

    def order_id(self, value, /):
        if isinstance(value, UUID):
            return value
        elif isinstance(value, str):
            if len(value) <= 255:
                return value
            else:
                raise ValueError("order_id must be less than 255 characters")
        else:
            raise TypeError("order_id must be a string or UUID")

    def description(self, value, /):
        # NOTE: API allows to request up to 49 720 characters,
        # but cuts to 2048 characters long
        return validate_string(value, max_len=2048, name="description")

    def amount(self, value, /):
        return validate_amount(value, "amount")

    def currency(self, value, /):
        if value in ("USD", "UAH", "EUR"):
            return value
        else:
            raise ValueError("currency must be USD, EUR or UAH")

    def expired_date(self, value, /):
        return validate_datetime(value, "expired_date")

    def date_from(self, value, /):
        return validate_dateedge(value, "date_from")

    def date_to(self, value, /):
        return validate_dateedge(value, "date_to")

    def resp_format(self, value, /):
        if value in ("json", "csv", "xml"):
            return value
        else:
            raise ValueError("format must be json, csv or xml")

    def phone(self, value, /):
        return validate_phone(value, "phone")

    def sender_phone(self, value, /):
        return validate_phone(value, "sender_phone")

    def info(self, value, /):
        if isinstance(value, str):
            return value
        else:
            raise TypeError("info must be a string")

    def language(self, value, /):
        if value in ("uk", "en"):
            return value
        else:
            raise ValueError("language must be uk or en")

    def ip(self, value, /):
        return IPv4Address(value)

    def card_number(self, value, /):
        return validate_digits(value, 16, "card_number")

    def card_cvv(self, value, /):
        return validate_digits(value, 3, "card_cvv")

    def card_exp_year(self, value, /):
        if isinstance(value, str):
            if fullmatch(r"(\d{2})?\d{2}", value):
                return value
            else:
                raise ValueError("card_exp_year must be 2 or 4 digits long")
        else:
            raise TypeError("card_exp_year must be a string of digits")

    def card_exp_month(self, value, /):
        if isinstance(value, str):
            if value.isdigit() and len(value) == 2 and (1 <= int(value) <= 12):
                return value
            else:
                raise ValueError(
                    "card_exp_month must be 2 digits long and between 01 and 12"
                )
        else:
            raise TypeError("card_exp_month must be a string containing 2 digits")

    def subscribe(self, value, /):
        return validate_one(value)

    def letter_of_credit(self, value, /):
        return validate_one(value)

    def recurringbytoken(self, value, /):
        return validate_one(value)

    def letter_of_credit_date(self, value, /):
        return validate_datetime(value, "letter_of_credit_date")

    def subscribe_periodicity(self, value, /):
        if value in ("month", "year"):
            return value
        else:
            raise ValueError("subscribe_periodicity must be month or year")

    def subscribe_date_start(self, value, /):
        return validate_datetime(value, "subscribe_date_start")

    def paytypes(self, value, /):
        valid, invalid = PayTypes([]), []
        if isinstance(value, Iterable):
            for item in value:
                if item in PayOption:
                    valid.append(str(item))
                else:
                    invalid.append(item)
            if len(invalid) == 0:
                return valid
            else:
                raise TypeError(
                    f"Invalid paytypes: {invalid}. Valid options are {', '.join(PayOption)}"
                )
        else:
            raise TypeError("paytypes must be an iterable")

    def customer(self, value, /):
        return validate_string(value, max_len=100, name="customer")

    def customer_user_id(self, value, /):
        if isinstance(value, str):
            return value
        else:
            raise TypeError("customer_user_id must be a string")

    def dae(self, value, /):
        if isinstance(value, (DetailAddenda, Mapping)):
            converted = False
            if not isinstance(value, DetailAddenda):
                converted = True
                value = DetailAddenda.from_dict(**value)

            errors = []
            for validation_fn in [
                lambda: validate_string(
                    value.air_line,
                    max_len=4,
                    name="dae.air_line" if converted else "dae.airLine",
                ),
                lambda: validate_string(
                    value.ticket_number,
                    max_len=15,
                    name="dae.ticket_number" if converted else "dae.ticketNumber",
                ),
                lambda: validate_string(
                    value.passenger_name,
                    max_len=29,
                    name="dae.passenger_name" if converted else "dae.passengerName",
                ),
                lambda: validate_string(
                    value.flight_number,
                    max_len=5,
                    name="dae.flight_number" if converted else "dae.flightNumber",
                ),
                lambda: validate_string(
                    value.origin_city,
                    max_len=5,
                    name="dae.origin_city" if converted else "dae.originCity",
                ),
                lambda: validate_string(
                    value.destination_city,
                    max_len=5,
                    name="dae.destination_city" if converted else "dae.destinationCity",
                ),
            ]:
                try:
                    validation_fn()
                except (TypeError, ValueError) as e:
                    errors.append(e)

            if len(errors) == 0:
                return value
            else:
                raise ExceptionGroup("Invalid dae (DetailAddenda)", errors)
        else:
            raise TypeError(
                f"dae must be a {DetailAddenda.__class__.__qualname__} or dict instance. Got {type(value).__name__} instead."
            )

    def split_rules(self, value, /):
        if isinstance(value, Iterable):
            if not isinstance(value, list):
                value = list(value)
            errors = []
            validated_rules = []
            for i, rule in enumerate(value):
                if isinstance(rule, (SplitRule, Mapping)):
                    if not isinstance(rule, SplitRule):
                        try:
                            rule = SplitRule(**rule)
                        except (TypeError, ValueError) as e:
                            errors.append(TypeError(f"Invalid split_rules[{i}]. {e}"))
                            continue

                    # Validate public_key
                    if not isinstance(rule.public_key, str):
                        errors.append(
                            TypeError(
                                f"Invalid split_rules[{i}].public_key. Must be a string."
                            )
                        )

                    # Validate amount
                    try:
                        validate_amount(rule.amount, f"split_rules[{i}].amount")
                    except (TypeError, ValueError) as e:
                        errors.append(e)

                    # Validate server_url
                    try:
                        validate_url(rule.server_url, f"split_rules[{i}].server_url")
                    except (TypeError, ValueError) as e:
                        errors.append(e)

                    # Validate commission_payer
                    if rule.commission_payer not in ("sender", "receiver"):
                        errors.append(
                            ValueError(
                                f"Invalid split_rules[{i}].commission_payer. Must be 'sender' or 'receiver'."
                            )
                        )

                    validated_rules.append(rule)
                else:
                    errors.append(
                        TypeError(
                            f"Invalid split_rules[{i}]. Must be a SplitRule or dict instance. Got {type(rule).__name__} instead."
                        )
                    )

            if len(errors) == 0:
                return SplitRules(validated_rules)
            else:
                raise ExceptionGroup("Invalid split_rules", errors)
        else:
            raise TypeError(
                f"split_rules must be an iterable. Got {type(value).__name__} instead."
            )

    def split_tickets_only(self, value, /):
        if isinstance(value, bool):
            return value
        else:
            raise TypeError("split_tickets_only must be a boolean")

    def rro_info(self, value, /):
        if isinstance(value, (FiscalInfo, Mapping)):
            if not isinstance(value, FiscalInfo):
                value = FiscalInfo(**value)
            errors = []
            for i, item in enumerate(value.items):
                if not isinstance(item.id, int):
                    errors.append(
                        TypeError(f"Invalid rro_info[{i}].id. Must be an integer.")
                    )
                elif item.id <= 0:
                    errors.append(
                        ValueError(
                            f"Invalid rro_info[{i}].id. Must be a positive integer."
                        )
                    )

                try:
                    validate_amount(item.amount, f"rro_info[{i}].amount")
                except (TypeError, ValueError) as e:
                    errors.append(e)

                try:
                    validate_amount(item.cost, f"rro_info[{i}].cost")
                except (TypeError, ValueError) as e:
                    errors.append(e)
                try:
                    validate_amount(item.price, f"rro_info[{i}].price")
                except (TypeError, ValueError) as e:
                    errors.append(e)

            if len(errors) == 0:
                return value
            else:
                raise ExceptionGroup("Invalid rro_info (FiscalInfo)", errors)
        else:
            raise TypeError(
                f"rro_info must be a {FiscalInfo.__class__.__qualname__} or dict instance. Got {type(value).__name__} instead."
            )

    def prepare(self, value, /):
        if value == "tariffs":
            return value
        elif value:
            return 1
        else:
            raise ValueError("prepare must be 1, True or 'tariffs'")

    def reccuring(self, value, /):
        return bool(value)

    def eci(self, value, /):
        if value in ("02", "05", "06", "07"):
            return value
        else:
            raise ValueError("eci must be '02', '05', '06' or '07'")

    def cavv(self, value, /):
        if isinstance(value, str):
            return value
        else:
            raise TypeError("cavv must be a string")

    def tdsv(self, value, /):
        if isinstance(value, str):
            return value
        else:
            raise TypeError("tdsv must be a string")

    def ds_trans_id(self, value, /):
        if isinstance(value, str):
            return value
        else:
            raise TypeError("dsTransID must be a string")

    def verifycode(self, value, /):
        return "Y" if value else None

    def server_url(self, value, /):
        return validate_url(validate_string(value, 510, name := "result_url"), name)

    def result_url(self, value, /):
        return validate_url(validate_string(value, 510, name := "result_url"), name)

    def product_url(self, value, /):
        return validate_string(value, max_len=2000, name="product_url")

    def product_description(self, value, /):
        return validate_string(value, max_len=500, name="product_description")

    def product_name(self, value, /):
        return validate_string(value, max_len=100, name="product_name")

    def product_category(self, value, /):
        return validate_string(value, max_len=25, name="product_category")
