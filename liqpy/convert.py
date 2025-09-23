from typing import overload
from decimal import Context, ROUND_HALF_EVEN
from functools import singledispatch
from datetime import datetime, timedelta, date, UTC


__all__ = [
    "DECTX",
    "noop",
    "to_date",
    "to_datetime",
    "to_milliseconds",
    "datetime_from_millis",
    "parse_isoduration",
    "DateTuple",
    "DateType",
]

DECTX = Context(prec=2, rounding=ROUND_HALF_EVEN)

DateTuple = tuple[int, int, int]  # (year, month, day)
DateType = date | datetime | str | float | int | DateTuple | timedelta


def noop[T](value: T, /) -> T:
    return value


def datetime_from_millis(value: int, /) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def parse_isoduration(value: str) -> timedelta:
    value = value.strip().upper()
    if value.startswith(("P", "-P")):
        sign = -1 if value.startswith("-") else 1
        value = value.lstrip("-").lstrip("P")
        dp, tp = value.split("T", 1) if "T" in value else (value, "")

        years, dp = dp.split("Y", 1) if "Y" in dp else ("", dp)
        months, dp = dp.split("M", 1) if "M" in dp else ("", dp)
        days, dp = dp.split("D", 1) if "D" in dp else ("", dp)
        assert dp == ""

        hours, tp = tp.split("H", 1) if "H" in tp else ("", tp)
        minutes, tp = tp.split("M", 1) if "M" in tp else ("", tp)
        seconds, tp = tp.split("S", 1) if "S" in tp else ("", tp)
        assert tp == ""

        return sign * timedelta(
            days=int(days or 0) + (int(years or 0) * 365) + (int(months or 0) * 30),
            hours=int(hours or 0),
            minutes=int(minutes or 0),
            seconds=int(seconds or 0),
        )

    else:
        raise ValueError(f"Invalid ISO 8601 duration: {value}")


@overload
def to_date(value: float, /) -> date: ...
@overload
def to_date(value: int, /) -> date: ...
@overload
def to_date(value: DateTuple, /) -> date: ...
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
def _(value: float):
    return date.fromtimestamp(value)


@to_date.register
def _(value: int):
    return date.fromtimestamp(value / 1e3)


@to_date.register
def _(value: tuple):
    year, month, day = value
    return date(year, month, day)


@overload
def to_datetime(value: datetime, /) -> datetime: ...
@overload
def to_datetime(value: date, /) -> datetime: ...
@overload
def to_datetime(value: float, /) -> datetime: ...
@overload
def to_datetime(value: int, /) -> datetime: ...
@overload
def to_datetime(value: str, /) -> datetime: ...
@overload
def to_datetime(value: DateTuple, /): ...
@overload
def to_datetime(value: timedelta, /) -> datetime: ...
@singledispatch
def to_datetime(value, /) -> datetime:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_datetime.register
def _(value: datetime, /):
    return value


@to_datetime.register
def _(value: date, /):
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


@to_datetime.register
def _(value: str, /):
    if value.startswith(("P", "-P")):
        return datetime.now(UTC) + parse_isoduration(value)
    else:
        return datetime.fromisoformat(value)


@to_datetime.register
def _(value: float, /):
    return datetime.fromtimestamp(value, UTC)


@to_datetime.register
def _(value: int, /):
    return datetime_from_millis(value)


@to_datetime.register
def _(value: tuple, /):
    year, month, day = value
    return datetime(year, month, day, tzinfo=UTC)


@to_datetime.register
def _(value: float, /):
    return datetime.fromtimestamp(value, UTC)


@to_datetime.register
def _(value: timedelta, /):
    return datetime.now(UTC) + value


@overload
def to_milliseconds(value: datetime, /) -> int: ...
@overload
def to_milliseconds(value: date, /) -> int: ...
@overload
def to_milliseconds(value: str, /) -> int: ...
@overload
def to_milliseconds(value: DateTuple, /): ...
@overload
def to_milliseconds(value: int, /) -> int: ...
@overload
def to_milliseconds(value: float, /) -> int: ...
@overload
def to_milliseconds(value: timedelta, /) -> int: ...
@singledispatch
def to_milliseconds(value, /) -> int:
    raise NotImplementedError(f"Unsupported type: {type(value)}")


@to_milliseconds.register
def _(value: int, /):
    return value


@to_milliseconds.register
def _(value: float, /):
    return int(round(value * 1e3))


@to_milliseconds.register
def _(value: datetime, /):
    return int(round(value.timestamp() * 1e3))


@to_milliseconds.register
def _(value: date, /):
    return to_milliseconds(to_datetime(value))


@to_milliseconds.register
def _(value: str, /):
    return to_milliseconds(to_datetime(value))


@to_milliseconds.register
def _(value: tuple, /):
    return to_milliseconds(to_datetime(value))


@to_milliseconds.register
def _(value: timedelta, /):
    return to_milliseconds(to_datetime(value))
