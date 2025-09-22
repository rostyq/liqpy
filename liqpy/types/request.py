from typing import Literal, TypedDict, Required, Iterable, NotRequired
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal
from ipaddress import IPv4Address

from liqpy.models.request import DetailAddenda, SplitRule, FiscalInfo

from .common import *


__all__ = [
    "LiqpayParams",
    "LiqpayRequest",
    "ReportsParams",
    "PaymentsParams",
    "CheckoutParams",
    "OtherDict",
    "ProductDict",
    "OneClickDict",
    "SenderOptionalDict",
    "CardDict",
    "SenderRequiredDict",
    "PayParams",
    "PaymentDict",
    "DateRangeEdge",
    "Prepare",
    "IdParams",
    "AmountIdParams",
    "DataParams",
    "TicketParams",
    "SubscribeParams",
]

Prepare = bool | Literal["tariffs"]

ElectronicCommerceIndicator = Literal["02", "05", "06", "07"]
DateRangeEdge = int | str | datetime | timedelta


class OtherDict(TypedDict, total=False):
    customer: str | None
    dae: DetailAddendaDict | DetailAddenda | None
    info: str | None


class ProductDict(TypedDict, total=False):
    product_category: str | None
    product_description: str | None
    product_name: str | None
    product_url: str | None


class OneClickDict(TypedDict, total=False):
    customer: str | None
    recurringbytoken: bool | None
    customer_user_id: str | None


class SenderOptionalDict(TypedDict, total=False):
    sender_address: str | None
    sender_city: str | None
    sender_country_code: str | None
    sender_first_name: str | None
    sender_last_name: str | None
    sender_postal_code: str | None


class CardDict(TypedDict):
    card: str
    card_exp_month: str
    card_exp_year: str
    card_cvv: NotRequired[str | None]


class UrlDict(TypedDict, total=False):
    result_url: str | None
    server_url: str | None


class SubscribeDict(TypedDict, total=False):
    subscribe: bool | None
    subscribe_date_start: str | datetime | timedelta | None
    subscribe_periodicity: SubscribePeriodicity | None


class LiqpayParams(
    OneClickDict,
    OtherDict,
    SenderOptionalDict,
    ProductDict,
    SubscribeDict,
    UrlDict,
    total=False,
):
    order_id: str | UUID | None
    payment_id: str | int | None

    amount: Decimal | str | None
    currency: Currency | None
    description: str | None

    rro_info: FiscalInfoDict | FiscalInfo | None
    expired_date: str | datetime | timedelta | None
    language: Language | None
    paytype: PayType | None
    paytypes: Iterable[PayOption] | None
    verifycode: bool | None
    email: str | None
    date_from: DateRangeEdge | None
    date_to: DateRangeEdge | None
    resp_format: Format | None

    prepare: Prepare | None
    tavv: str | None
    tid: str | None

    split_rules: Iterable[SplitRuleDict | SplitRule] | None
    split_tickets_only: bool | None

    ip: str | int | IPv4Address | None

    card: str | None
    card_exp_month: str | None
    card_exp_year: str | None
    card_cvv: str | None

    phone: str | None
    sender_phone: str | None
    sender_email: str | None
    sender_shipping_state: str | None

    mpi_md: str | None
    mpi_pares: str | None

    letter_of_credit: bool | None
    letter_of_credit_date: str | datetime | timedelta | None

    recurring: bool | None
    eci: ElectronicCommerceIndicator | None
    cavv: str | None
    tdsv: str | None
    ds_trans_id: str | None


class LiqpayRequest(LiqpayDict, LiqpayParams):
    pass


class PaymentsParams(TypedDict):
    date_from: DateRangeEdge
    date_to: DateRangeEdge


class ReportsParams(PaymentsParams, total=False):
    resp_format: Format | None


class PaymentDict(TypedDict, total=True):
    order_id: str | UUID
    amount: Decimal | str
    currency: Currency
    description: str


class SenderRequiredDict(SenderOptionalDict, total=False):
    phone: Required[str]
    sender_address: Required[str]
    sender_city: Required[str]
    sender_postal_code: Required[str]
    sender_email: str | None
    sender_country_code: Required[str]
    sender_state: str | None
    sender_shipping_state: str | None


class CheckoutParams(
    PaymentDict,
    SenderOptionalDict,
    OneClickDict,
    OtherDict,
    SubscribeDict,
    ProductDict,
    UrlDict,
    total=False,
):
    action: Required[CheckoutAction]
    language: Language | None
    expired_date: str | datetime | timedelta | None
    paytypes: Iterable[PayOption] | None
    split_rules: Iterable[SplitRuleDict | SplitRule] | None
    rro_info: FiscalInfoDict | FiscalInfo | None
    verifycode: bool | None


class PayParams(
    PaymentDict, CardDict, OtherDict, UrlDict, SubscribeDict, ProductDict, total=False
):
    ip: str | int | IPv4Address | None
    language: Language | None
    paytype: PayType | None
    tavv: str | None
    tid: str | None

    prepare: Prepare | None
    recurringbytoken: bool | None
    recurring: bool | None
    eci: ElectronicCommerceIndicator | None
    cavv: str | None
    tdsv: str | None
    ds_trans_id: str | None

    rro_info: FiscalInfoDict | FiscalInfo | None
    split_rules: Iterable[SplitRuleDict | SplitRule] | None
    split_tickets_only: bool | None


class SubscribeParams(
    PaymentDict,
    CardDict,
    SenderOptionalDict,
    OtherDict,
    ProductDict,
    total=False,
):
    subscribe_date_start: Required[str | datetime | timedelta]
    subscribe_periodicity: Required[SubscribePeriodicity]
    phone: str | None
    language: Language | None
    ip: str | int | IPv4Address
    prepare: Prepare | None
    recurringbytoken: bool | None
    recurring: bool | None
    server_url: str | None


class IdParams(TypedDict, total=False):
    order_id: str | UUID | None
    payment_id: str | int | None


class AmountIdParams(IdParams, total=False):
    amount: Decimal | str | None


class DataParams(IdParams):
    info: str


class TicketParams(IdParams):
    order_id: str | UUID
    email: str
    language: NotRequired[Language | None]
