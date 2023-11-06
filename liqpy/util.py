from typing import overload, TYPE_CHECKING, Literal, Any
from functools import singledispatch
from numbers import Number
from datetime import datetime
from urllib.parse import urlparse
from dataclasses import dataclass


@dataclass
class DetailAddenda:
    air_line: str
    ticket_number: str
    passenger_name: str
    flight_number: str
    origin_city: str
    destination_city: str
    departure_date: datetime

    def __post_init__(self):
        assert (
            len(self.air_line) <= 4
        ), "Invalid air_line. Must be less than 4 characters."
        assert (
            len(self.ticket_number) <= 15
        ), "Invalid ticket_number. Must be less than 15 characters."
        assert (
            len(self.passenger_name) <= 29
        ), "Invalid passenger_name. Must be less than 29 characters."
        assert (
            len(self.flight_number) <= 5
        ), "Invalid flight_number. Must be less than 5 characters."
        assert (
            len(self.origin_city) <= 5
        ), "Invalid origin_city. Must be less than 5 characters."
        assert (
            len(self.destination_city) <= 5
        ), "Invalid destination_city. Must be less than 5 characters."


@dataclass
class SplitRule:
    public_key: str
    amount: Number
    commission_payer: Literal["sender", "receiver"]
    server_url: str

    def __post_init__(self):
        assert isinstance(self.public_key, str), "Invalid public_key. Must be a string."
        assert isinstance(self.amount, Number), "Invalid amount. Must be a number."
        assert self.amount > 0, "Invalid amount. Must be greater than 0."
        assert self.commission_payer in (
            "sender",
            "receiver",
        ), "Invalid commission_payer. Must be sender or receiver."
        verify_url(self.server_url)


@dataclass
class FiscalData:
    id: int
    amount: Number
    cost: Number
    price: Number

    def __post_init__(self):
        assert isinstance(self.id, int), "Invalid id. Must be an integer."
        for value in (self.amount, self.cost, self.price):
            assert isinstance(value, Number), "Invalid amount. Must be a number."
            assert value > 0, "Invalid amount. Must be greater than 0."


def is_sandbox(key: str, /) -> bool:
    return key.startswith("sandbox_")


def verify_url(value: str):
    assert len(value) <= 500, "Invalid URL. Must be less than 500 characters."
    result = urlparse(value or "")
    assert result.scheme in (
        "http",
        "https",
    ), "Invalid URL scheme. Must be http or https."
    assert result.netloc != "", "Invalid URL. Must be a valid URL."


def update_keys(dst: dict[str, Any], keys: set[str], data: dict[str, Any]):
    for key in keys:
        value = data.pop(key, None)

        if value is None:
            continue

        assert isinstance(value, str)
        dst[key] = value


@singledispatch
def to_milliseconds(value) -> int:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_milliseconds.register
def _(value: Number):
    return int(round(value * 1000))


@to_milliseconds.register
def _(value: datetime):
    return to_milliseconds(value.timestamp())


@to_milliseconds.register
def _(value: str):
    return to_milliseconds(datetime.fromisoformat(value))


if TYPE_CHECKING:

    @overload
    def to_milliseconds(value: Number) -> int:
        ...

    @overload
    def to_milliseconds(value: datetime) -> int:
        ...

    @overload
    def to_milliseconds(value: str) -> int:
        ...
