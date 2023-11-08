from typing import overload, TYPE_CHECKING
from functools import singledispatch, cache
from numbers import Number
from datetime import datetime, UTC
from re import compile


@cache
def date_pattern(flags: int = 0):
    return compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", flags=flags)


@singledispatch
def to_datetime(value, **kwargs) -> datetime:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_datetime.register
def _(value: datetime, **kwargs):
    return value


@to_datetime.register
def _(value: str, **kwargs):
    if date_pattern().fullmatch(value):
        return datetime.strptime(value, r"%Y-%m-%d %H:%M:%S")
    else:
        return datetime.fromisoformat(value)


@to_datetime.register
def _(value: Number, **kwargs):
    return datetime.fromtimestamp(float(value), tz=UTC)


@singledispatch
def to_milliseconds(value, **kwargs) -> int:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_milliseconds.register
def _(value: int, **kwargs):
    return value


@to_milliseconds.register
def _(value: datetime, **kwargs):
    return int(value.timestamp() * 1000)


@to_milliseconds.register
def _(value: str, **kwargs):
    return to_milliseconds(to_datetime(value, **kwargs))


if TYPE_CHECKING:

    @overload
    def to_datetime(value: Number, **kwargs) -> datetime:
        ...

    @overload
    def to_datetime(value: datetime, **kwargs) -> datetime:
        ...

    @overload
    def to_datetime(value: str, **kwargs) -> datetime:
        ...

    @overload
    def to_milliseconds(value: datetime, **kwargs) -> int:
        ...

    @overload
    def to_milliseconds(value: str, **kwargs) -> int:
        ...

    @overload
    def to_milliseconds(value: int, **kwargs) -> int:
        ...
