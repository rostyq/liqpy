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
        s: str = data["departureDate"]
        return cls(
            air_line=data["airLine"],
            ticket_number=data["ticketNumber"],
            passenger_name=data["passengerName"],
            flight_number=data["flightNumber"],
            origin_city=data["originCity"],
            destination_city=data["destinationCity"],
            departure_date=date(2000 + int(s[:2]), int(s[2:4]), int(s[4:])),
        )


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
