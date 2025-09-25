from typing import Literal, Union, TypedDict
from decimal import Decimal

from liqpy.models.request import FiscalItem

__all__ = [
    "Language",
    "Currency",
    "Format",
    "PayType",
    "PayOption",
    "SubscribePeriodicity",
    "CallbackAction",
    "CheckoutAction",
    "LiqpayAction",
    "ThreeDS",
    "SubscriptionStatus",
    "ErrorStatus",
    "SuccessStatus",
    "FinalStatus",
    "ConfirmationStatus",
    "OtherStatus",
    "LiqpayStatus",
    "CallbackStatus",
    "DetailAddendaDict",
    "SplitRuleDict",
    "FiscalItemDict",
    "FiscalInfoDict",
    "LiqpayDict",
    "BonusType",
    "Amount",
]


Language = Literal["uk", "en"]
Currency = Literal["UAH", "USD", "EUR"]
Format = Literal["json", "xml", "csv"]

PayType = Literal[
    "apay",
    "gpay",
    "apay_tavv",
    "gpay_tavv",
    "tavv",
]
PayOption = Literal[
    "card", "liqpay", "privat24", "masterpass", "moment_part", "cash", "invoice", "qr"
]
SubscribePeriodicity = Literal["month", "year"]

CheckoutAction = Literal["auth", "pay", "hold", "subscribe", "paydonate"]
CallbackAction = Union[CheckoutAction, Literal["paysplit", "regular", "refund"]]
LiqpayAction = Union[
    CallbackAction,
    Literal[
        "payqr",
        "paytoken",
        "paycash",
        "hold_completion",
        "split_rules",
        "letter_of_credit",
        "apay",
        "gpay",
        "payment_prepare",
        "p2pcredit",
        "p2pdebit",
        "confirm",
        "mpi",
        "cardverification",
        "register",
        "data",
        "ticket",
        "status",
        "invoice_send",
        "invoice_cancel",
        "token_create",
        "token_create_unique",
        "token_update",
        "reports",
        "reports_compensation",
        "reports_compensation_file",
        "agent_shop_create",
        "agent_shop_edit",
        "agent_info_merchant",
        "agent_info_user",
        "unsubscribe",
        "subscribe_update",
    ],
]

SubscriptionStatus = Literal["subscribed", "unsubscribed"]
ErrorStatus = Literal["error", "failure"]
SuccessStatus = Literal["success"]
FinalStatus = Union[ErrorStatus, Literal["reversed"], SuccessStatus]
ConfirmationStatus = Literal[
    "3ds_verify",
    "captcha_verify",
    "cvv_verify",
    "ivr_verify",
    "otp_verify",
    "password_verify",
    "phone_verify",
    "pin_verify",
    "receiver_verify",
    "sender_verify",
    "senderapp_verify",
    "wait_qr",
    "wait_sender",
]
OtherStatus = Literal[
    "cash_wait",
    "hold_wait",
    "invoice_wait",
    "prepared",
    "processing",
    "wait_accept",
    "wait_card",
    "wait_compensation",
    "wait_lc",
    "wait_reserve",
    "wait_secure",
]
LiqpayStatus = CallbackStatus = Union[
    SubscriptionStatus, FinalStatus, ConfirmationStatus, OtherStatus
]

Amount = Decimal | str | int
ThreeDS = Literal[5, 6, 7]
BonusType = Literal["bonusplus", "discount_club", "personal", "promo"]


class LiqpayDict(TypedDict):
    version: int
    public_key: str
    action: LiqpayAction


class DetailAddendaDict(TypedDict):
    airLine: str
    ticketNumber: str
    passengerName: str
    flightNumber: str
    originCity: str
    destinationCity: str
    departureDate: str


class SplitRuleDict(TypedDict):
    public_key: str
    amount: Decimal | str
    commission_payer: Literal["sender", "receiver"]
    server_url: str


class FiscalItemDict(TypedDict):
    id: int
    amount: Decimal | str
    cost: Decimal | str
    price: Decimal | str


class FiscalInfoDict(TypedDict):
    items: list[FiscalItemDict | FiscalItem]
    delivery_emails: list[str]


class ProductInfo(TypedDict, total=False):
    product_category: str
    product_description: str
    product_name: str
    product_url: str
