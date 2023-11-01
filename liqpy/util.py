from typing import overload, TYPE_CHECKING
from functools import singledispatch
from numbers import Number
from datetime import datetime
from urllib.parse import urlparse


if TYPE_CHECKING:
    from .types import RequestForm


def to_dict(data: str, signature: str, /) -> "RequestForm":
    """Convert data and signature into a dictionary."""
    return {"data": data, "signature": signature}


def filter_none(data: dict, /) -> dict:
    return {key: value for key, value in data.items() if value is not None}


def is_sandbox(key: str, /) -> bool:
    return key.startswith("sandbox_")


def verify_url(value: str):
    assert len(value) <= 500, "Invalid URL. Must be less than 500 characters."
    result = urlparse(value or "")
    assert result.scheme in ("http", "https"), "Invalid URL scheme. Must be http or https."
    assert result.netloc != "", "Invalid URL. Must be a valid URL."


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


@singledispatch
def format_date(value) -> str:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@format_date.register
def _(value: datetime):
    return value.strftime("%Y-%m-%d %H:%M:%S")


@format_date.register
def _(value: str):
    return format_date(datetime.fromisoformat(value))


@format_date.register
def _(value: Number):
    return format_date(datetime.fromtimestamp(value))


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

    @overload
    def format_date(value: Number) -> str:
        ...

    @overload
    def format_date(value: datetime) -> str:
        ...

    @overload
    def format_date(value: str) -> str:
        ...
