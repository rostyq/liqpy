from typing import overload, SupportsFloat
from decimal import Decimal, Context, ROUND_HALF_EVEN
from functools import singledispatch
from datetime import datetime, timedelta, date, UTC


__all__ = [
    "DECTX",
    "noop",
    "to_date",
    "to_datetime",
    "to_milliseconds",
    "datetime_from_millis",
]

DECTX = Context(prec=2, rounding=ROUND_HALF_EVEN)


def noop[T](value: T, /) -> T:
    return value


def datetime_from_millis(value: int, /) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


@overload
def to_date(value: SupportsFloat, /) -> date: ...
@overload
def to_date(value: date, /) -> date: ...
@overload
def to_date(value: str, /) -> date: ...
@overload
def to_date(value: timedelta, /) -> date: ...
@singledispatch
def to_date(value, /) -> date:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_date.register
def _(value: datetime):
    return value.date()


@to_date.register
def _(value: date):
    return value


@to_date.register
def _(value: str):
    return date.fromisoformat(value)


@to_date.register
def _(value: timedelta):
    return date.today() + value


@to_date.register
def _(value: SupportsFloat):
    return date.fromtimestamp(float(value))


@overload
def to_datetime(value: datetime, /) -> datetime: ...
@overload
def to_datetime(value: str, /) -> datetime: ...
@overload
def to_datetime(value: timedelta, /) -> datetime: ...
@singledispatch
def to_datetime(value, /) -> datetime:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_datetime.register
def _(value: datetime, /):
    return value


@to_datetime.register
def _(value: str, /):
    return datetime.fromisoformat(value)


@to_datetime.register
def _(value: SupportsFloat, /):
    return datetime.fromtimestamp(float(value), UTC)


@to_datetime.register
def _(value: timedelta, /):
    return datetime.now(UTC) + value


@overload
def to_milliseconds(value: datetime, /) -> int: ...
@overload
def to_milliseconds(value: str, /) -> int: ...
@overload
def to_milliseconds(value: int, /) -> int: ...
@overload
def to_milliseconds(value: timedelta, /) -> int: ...
@singledispatch
def to_milliseconds(value, /) -> int:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_milliseconds.register
def _(value: int, /):
    return value


@to_milliseconds.register
def _(value: datetime, /):
    return int(round(value.timestamp() * 1e3))


@to_milliseconds.register
def _(value: str, /):
    return to_milliseconds(to_datetime(value))


@to_milliseconds.register
def _(value: timedelta, /):
    return to_milliseconds(to_datetime(value))
