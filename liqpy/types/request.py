from typing import Literal, TypedDict, Required, List
from numbers import Number
from datetime import datetime, timedelta
from uuid import UUID

from liqpy.models.request import FiscalItem, DetailAddenda, SplitRule, FiscalInfo

from .common import SubscribePeriodicity, Language, PayType, PayOption, Format
from .action import Action


class DetailAddendaDict(TypedDict):
    airLine: str
    ticketNumber: str
    passengerName: str
    flightNumber: str
    originCity: str
    destinationCity: str
    departureDate: str


class SplitRuleDict(TypedDict, total=False):
    public_key: Required[str]
    amount: Required[Number]
    commission_payer: Required[Literal["sender", "receiver"]]
    server_url: Required[str]


class FiscalItemDict(TypedDict):
    id: int
    amount: Number
    cost: Number
    price: Number


class FiscalInfoDict(TypedDict, total=False):
    items: List[FiscalItemDict | FiscalItem]
    delivery_emails: List[str]


class ProductDict(TypedDict, total=False):
    product_category: str
    product_description: str
    product_name: str
    product_url: str


class OneClickDict(TypedDict, total=False):
    customer: str
    recurringbytoken: Literal["1", True]
    customer_user_id: str


class SubscribeDict(TypedDict, total=False):
    subscribe: Literal[1, True]
    subscribe_date_start: str | datetime | timedelta
    subscribe_periodicity: SubscribePeriodicity


class LetterDict(TypedDict, total=False):
    letter_of_credit: Literal[1, True]
    letter_of_credit_date: str | datetime | timedelta


class MPIParamsDict(TypedDict, total=False):
    mpi_md: str
    mpi_pares: str


class SenderDict(TypedDict, total=False):
    phone: str
    sender_phone: str
    sender_first_name: str
    sender_last_name: str
    sender_email: str
    sender_country_code: str
    sender_city: str
    sender_address: str
    sender_postal_code: str
    sender_shipping_state: str


class CardDict(TypedDict, total=False):
    card: Required[str]
    card_exp_month: str
    card_exp_year: str
    card_cvv: str


class BaseRequestDict(TypedDict, total=False):
    version: Required[int]
    public_key: Required[str]
    action: Required["Action"]


class LiqpayRequestDict(
    CardDict,
    SenderDict,
    MPIParamsDict,
    LetterDict,
    SubscribeDict,
    OneClickDict,
    ProductDict,
    total=False,
):
    order_id: str | UUID
    amount: Number | str
    rro_info: FiscalInfoDict | FiscalInfo
    expired_date: str | datetime | timedelta
    language: Language
    paytype: PayType
    paytypes: PayOption
    result_url: str
    server_url: str
    verifycode: Literal["Y", True]
    email: str
    date_from: int | datetime | timedelta
    date_to: int | datetime | timedelta
    resp_format: Format
    split_rules: list[SplitRuleDict | SplitRule]
    dae: DetailAddendaDict | DetailAddenda
    info: str
