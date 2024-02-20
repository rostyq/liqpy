from typing import Literal
from dataclasses import dataclass
from datetime import date
from numbers import Number

from liqpy.util.convert import to_date


@dataclass(kw_only=True)
class DetailAddenda:
    air_line: str
    ticket_number: str
    passenger_name: str
    flight_number: str
    origin_city: str
    destination_city: str
    departure_date: date

    def __post_init__(self):
        self.departure_date = to_date(self.departure_date)

    @classmethod
    def from_json(cls, data: dict):
        s: str = data.get("departureDate") or data.get("departure_date")
        return cls(
            air_line=data.get("airLine") or data.get("air_line"),
            ticket_number=data.get("ticketNumber") or data.get("ticket_number"),
            passenger_name=data.get("passengerName") or data.get("passenger_name"),
            flight_number=data.get("flightNumber") or data.get("flight_number"),
            origin_city=data.get("originCity") or data.get("origin_city"),
            destination_city=data.get("destinationCity")
            or data.get("destination_city"),
            departure_date=date(2000 + int(s[:2]), int(s[2:4]), int(s[4:])),
        )

    def to_json(self):
        return {
            "airLine": self.air_line,
            "ticketNumber": self.ticket_number,
            "passengerName": self.passenger_name,
            "flightNumber": self.flight_number,
            "originCity": self.origin_city,
            "destinationCity": self.destination_city,
            "departureDate": self.departure_date.strftime(r"%y%m%d"),
        }


@dataclass(kw_only=True)
class SplitRule:
    public_key: str
    amount: Number
    commission_payer: Literal["sender", "receiver"]
    server_url: str


@dataclass(kw_only=True)
class FiscalItem:
    id: int
    amount: Number
    cost: Number
    price: Number


@dataclass(kw_only=True)
class FiscalInfo:
    items: list[FiscalItem]
    delivery_emails: list[str]
