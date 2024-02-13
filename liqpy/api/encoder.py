from functools import singledispatchmethod
from dataclasses import asdict

from base64 import b64encode
from json import JSONEncoder

from uuid import UUID
from decimal import Decimal
from datetime import date, datetime, UTC

from liqpy.models.request import FiscalItem, DetailAddenda, SplitRule


__all__ = ("Encoder", "JSONEncoder")


class Encoder(JSONEncoder):
    """Custom JSON encoder for LiqPay API requests"""

    date_fmt = r"%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(
            skipkeys=False,
            ensure_ascii=True,
            check_circular=True,
            allow_nan=False,
            sort_keys=False,
            indent=None,
            separators=None,
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
        return o.astimezone(UTC).strftime(self.date_fmt)

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
        data = {
            "airLine": o.air_line,
            "ticketNumber": o.ticket_number,
            "passengerName": o.passenger_name,
            "flightNumber": o.flight_number,
            "originCity": o.origin_city,
            "destinationCity": o.destination_city,
            "departureDate": o.departure_date.strftime(r"%d%m%y"),
        }

        return b64encode(self.encode(data).encode()).decode()

    @default.register
    def _(self, o: SplitRule) -> dict:
        return asdict(o)

    @default.register
    def _(self, o: FiscalItem) -> dict:
        return asdict(o)
