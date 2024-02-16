from typing import overload, TYPE_CHECKING
from functools import singledispatch
from numbers import Number
from datetime import datetime, timedelta, date

from liqpy.constants import LIQPAY_TZ


def from_milliseconds(value: int, tz=LIQPAY_TZ) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=tz)


@singledispatch
def to_date(value, **kwargs) -> date:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_date.register
def _(value: datetime, **kwargs):
    return value.date()


@to_date.register
def _(value: date, **kwargs):
    return value


@to_date.register
def _(value: str, **kwargs):
    return date.fromisoformat(value)


@to_date.register
def _(value: timedelta, **kwargs):
    return date.today() + value


@to_date.register
def _(value: Number, **kwargs):
    return to_date(date.fromtimestamp(float(value)))


@singledispatch
def to_datetime(value, **kwargs) -> datetime:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_datetime.register
def _(value: datetime, **kwargs):
    return value


@to_datetime.register
def _(value: str, **kwargs):
    return datetime.fromisoformat(value)


@to_datetime.register
def _(value: Number, tz=LIQPAY_TZ, **kwargs):
    return datetime.fromtimestamp(float(value), tz=tz)


@to_datetime.register
def _(value: timedelta, tz=LIQPAY_TZ, **kwargs):
    return datetime.now(tz) + value


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


@to_milliseconds.register
def _(value: timedelta, **kwargs):
    return to_milliseconds(to_datetime(value, **kwargs))


if TYPE_CHECKING:
    @overload
    def to_date(value: Number, **kwargs) -> date:
        ...

    @overload
    def to_date(value: date, **kwargs) -> date:
        ...

    @overload
    def to_date(value: str, **kwargs) -> date:
        ...

    @overload
    def to_date(value: timedelta, **kwargs) -> date:
        ...

    @overload
    def to_date(value: Number, **kwargs) -> date:
        ...

    @overload
    def to_datetime(value: datetime, **kwargs) -> datetime:
        ...

    @overload
    def to_datetime(value: str, **kwargs) -> datetime:
        ...

    @overload
    def to_datetime(value: timedelta, **kwargs) -> datetime:
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

    @overload
    def to_milliseconds(value: timedelta, **kwargs) -> int:
        ...
