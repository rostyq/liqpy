from typing import Literal, TYPE_CHECKING, cast
from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal
from collections import UserList
from enum import StrEnum

from liqpy.convert import to_date

if TYPE_CHECKING:
    from liqpy.types import FiscalItemDict
    from liqpy.types.request import (
        DetailAddendaDict,
        FiscalInfoDict,
        SplitRuleDict,
    )


class PayType(StrEnum):
    APAY = "apay"
    GPAY = "gpay"
    APAY_TAVV = "apay_tavv"
    GPAY_TAVV = "gpay_tavv"
    TAVV = "tavv"


class PayOption(StrEnum):
    CARD = "card"
    LIQPAY = "liqpay"
    PRIVAT24 = "privat24"
    MASTERPASS = "masterpass"
    MOMENT_PART = "moment_part"
    CASH = "cash"
    INVOICE = "invoice"
    QR = "qr"


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
    def from_dict(cls, data: "DetailAddendaDict"):
        s = data["departureDate"]
        return cls(
            air_line=data["airLine"],
            ticket_number=data["ticketNumber"],
            passenger_name=data["passengerName"],
            flight_number=data["flightNumber"],
            origin_city=data["originCity"],
            destination_city=data["destinationCity"],
            departure_date=date(2000 + int(s[:2]), int(s[2:4]), int(s[4:])),
        )

    def to_dict(self) -> "DetailAddendaDict":
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
    amount: Decimal
    commission_payer: Literal["sender", "receiver"]
    server_url: str

    def to_dict(self):
        return cast("SplitRuleDict", asdict(self))


class SplitRules(UserList[SplitRule]):
    def to_list(self) -> list["SplitRuleDict"]:
        return [rule.to_dict() for rule in self.data]


@dataclass(kw_only=True)
class FiscalItem:
    id: int
    amount: Decimal
    cost: Decimal
    price: Decimal

    def __post_init__(self):
        self.amount = Decimal(self.amount)
        self.cost = Decimal(self.cost)
        self.price = Decimal(self.price)

    def to_dict(self):
        return cast("FiscalItemDict", asdict(self))


@dataclass(kw_only=True)
class FiscalInfo:
    items: list[FiscalItem]
    delivery_emails: list[str]

    def __post_init__(self):
        self.items = [
            item if isinstance(item, FiscalItem) else FiscalItem(**item)
            for item in self.items
        ]
        self.delivery_emails = [str(email) for email in self.delivery_emails]

    def to_dict(self) -> "FiscalInfoDict":
        return {
            "items": [item.to_dict() for item in self.items],
            "delivery_emails": self.delivery_emails,
        }


class PayTypes(UserList[str]):
    pass
