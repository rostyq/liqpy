from functools import singledispatchmethod
from dataclasses import asdict

from base64 import b64encode
from json import JSONEncoder

from uuid import UUID
from decimal import Decimal
from datetime import date, datetime, UTC

from liqpy.models.request import FiscalItem, DetailAddenda, SplitRule
from liqpy.constants import DATE_FORMAT


__all__ = ("Encoder", "JSONEncoder", "SEPARATORS")


SEPARATORS = (",", ":")


class Encoder(JSONEncoder):
    """Custom JSON encoder for LiqPay API requests"""

    date_fmt = DATE_FORMAT

    tz = UTC

    def __init__(self) -> None:
        super().__init__(
            skipkeys=False,
            ensure_ascii=True,
            check_circular=True,
            allow_nan=False,
            sort_keys=False,
            indent=None,
            separators=SEPARATORS,
            default=None,
        )

    @singledispatchmethod
    def default(self, o):
        return super().default(o)

    @default.register
    def _(self, o: Decimal) -> float:
        return round(float(o), 4)

    @default.register
    def _(self, o: datetime) -> str:
        return o.astimezone(self.tz).strftime(self.date_fmt)

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
        return b64encode(self.encode(o.to_json()).encode()).decode()

    @default.register
    def _(self, o: SplitRule) -> dict:
        return asdict(o)

    @default.register
    def _(self, o: FiscalItem) -> dict:
        return asdict(o)
