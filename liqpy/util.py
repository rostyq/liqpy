from typing import overload, TYPE_CHECKING
from functools import singledispatch
from numbers import Number
from datetime import datetime


if TYPE_CHECKING:
    from .types import RequestForm


def to_dict(data: str, signature: str, /) -> "RequestForm":
    """Convert data and signature into a dictionary."""
    return {"data": data, "signature": signature}


def is_sandbox(key: str, /) -> bool:
    return key.startswith("sandbox_")


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
