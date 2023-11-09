from typing import Literal, TYPE_CHECKING, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from numbers import Number
from ipaddress import ip_address, IPv4Address

from .convert import to_datetime

if TYPE_CHECKING:
    from .types.common import Currency, Language, PayType
    from .types.callback import ThreeDS, CallbackAction
    from .types.error import LiqPayErrcode
    from .types import status


def from_milliseconds(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000)


@dataclass(kw_only=True)
class DetailAddenda:
    air_line: str
    ticket_number: str
    passenger_name: str
    flight_number: str
    origin_city: str
    destination_city: str
    departure_date: datetime

    def __post_init__(self):
        if not isinstance(self.departure_date, datetime):
            self.departure_date = to_datetime(self.departure_date)

    def to_dict(self):
        return {
            "airLine": self.air_line,
            "ticketNumber": self.ticket_number,
            "passengerName": self.passenger_name,
            "flightNumber": self.flight_number,
            "originCity": self.origin_city,
            "destinationCity": self.destination_city,
            "departureDate": self.departure_date.strftime(r"%d%m%y"),
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


@dataclass(init=False)
class LiqpayCallback:
    acq_id: int
    action: "CallbackAction"
    agent_commission: Number
    amount: Number
    amount_bonus: Number
    amount_credit: Number
    amount_debit: Number
    authcode_credit: str | None = None
    authcode_debit: str | None = None
    card_token: str | None = None
    commission_credit: Number
    commission_debit: Number
    completion_date: datetime | None = None
    create_date: datetime
    currency: "Currency"
    currency_credit: "Currency"
    currency_debit: "Currency"
    customer: str | None = None
    description: str
    end_date: datetime
    err_code: Optional["LiqPayErrcode"] = None
    err_description: str | None = None
    info: str | None = None
    ip: IPv4Address | None = None
    is_3ds: bool
    language: "Language"
    liqpay_order_id: str
    mpi_eci: "ThreeDS"
    order_id: str
    payment_id: int
    paytype: "PayType"
    public_key: str
    receiver_commission: Number
    redirect_to: str | None = None
    refund_date_last: datetime | None = None
    rrn_credit: str | None = None
    rrn_debit: str | None = None
    sender_bonus: Number
    sender_card_bank: str
    sender_card_country: int
    sender_card_mask2: str
    sender_card_type: str
    sender_commission: Number
    sender_first_name: str | None = None
    sender_last_name: str | None = None
    sender_phone: str | None = None
    status: "status.CallbackStatus"
    transaction_id: str | None = None
    token: str | None = None
    type: str
    version: Literal[3]
    err_erc: Optional["LiqPayErrcode"] = None
    product_category: str | None = None
    product_description: str | None = None
    product_name: str | None = None
    product_url: str | None = None
    refund_amount: Number | None = None
    verifycode: str | None = None

    code: str | None = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        self.__post_init__()

    def __post_init__(self):
        self.create_date = from_milliseconds(self.create_date)
        self.end_date = from_milliseconds(self.end_date)

        if self.completion_date is not None:
            self.completion_date = from_milliseconds(self.completion_date)

        if self.refund_date_last is not None:
            self.refund_date_last = from_milliseconds(self.refund_date_last)

        if self.ip is not None:
            self.ip = ip_address(self.ip)

        self.mpi_eci = int(self.mpi_eci)
