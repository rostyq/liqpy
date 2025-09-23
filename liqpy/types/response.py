from typing import Literal, TypedDict, NotRequired

from decimal import Decimal
from datetime import datetime
from ipaddress import IPv4Address

from .error import LiqPayErrcode
from . import (
    Currency,
    PayType,
    Language,
    FinalStatus,
    CallbackStatus,
    ThreeDS,
    LiqpayDict,
    LiqpayAction,
    ProductInfo,
    BonusType,
)


__all__ = [
    "LiqpayCallbackDict",
    "LiqpayRefundDict",
    "PayResult",
    "HoldResult",
    "CorePaymentDict",
    "TransactionDict",
    "CommissionBonusDict",
    "SenderCardDict",
    "SecurityDict",
    "DatesDict",
    "SystemDict",
    "ErrorDict",
]


class CorePaymentDict(TypedDict):
    acq_id: int
    action: LiqpayAction
    amount: Decimal
    currency: Currency
    description: str
    order_id: str
    payment_id: int
    liqpay_order_id: str
    paytype: NotRequired[PayType]
    status: CallbackStatus


class TransactionDict(TypedDict, total=False):
    amount_credit: Decimal
    amount_debit: Decimal
    currency_credit: str
    currency_debit: str
    authcode_credit: str
    authcode_debit: str
    rrn_credit: str
    rrn_debit: str
    transaction_id: int


class CommissionBonusDict(TypedDict, total=False):
    agent_commission: Decimal
    amount_bonus: Decimal
    commission_credit: Decimal
    commission_debit: Decimal
    receiver_commission: Decimal
    sender_bonus: Decimal
    sender_commission: Decimal
    bonus_procent: Decimal


class SenderCardDict(TypedDict, total=False):
    card_token: str
    sender_card_bank: str
    sender_card_country: str
    sender_card_mask2: str
    sender_card_type: str
    sender_first_name: str
    sender_last_name: str
    sender_phone: str


class SecurityDict(TypedDict, total=False):
    is_3ds: bool
    mpi_eci: ThreeDS
    mpi_cres: str
    ip: IPv4Address


class DatesDict(TypedDict, total=False):
    create_date: datetime
    end_date: datetime
    completion_date: datetime
    reserve_date: datetime
    refund_date_last: datetime


class SystemDict(TypedDict, total=False):
    language: Language
    confirm_phone: str


class ErrorDict(TypedDict, total=False):
    err_code: LiqPayErrcode
    err_description: str
    err_erc: LiqPayErrcode


class LiqpayCallbackDict(
    LiqpayDict,
    CorePaymentDict,
    TransactionDict,
    CommissionBonusDict,
    SenderCardDict,
    SecurityDict,
    DatesDict,
    ProductInfo,
    ErrorDict,
    total=False,
):
    type: Literal["buy", "hold", "regular"]
    customer: str
    info: str
    redirect_to: str
    token: str
    refund_amount: Decimal
    verifycode: str
    wait_reserve_status: bool


class PayResult(
    LiqpayDict,
    CorePaymentDict,
    TransactionDict,
    CommissionBonusDict,
    SenderCardDict,
    SecurityDict,
    DatesDict,
    SystemDict,
    total=False,
):
    bonus_type: BonusType


class HoldResult(
    LiqpayDict,
    CorePaymentDict,
    TransactionDict,
    CommissionBonusDict,
    SenderCardDict,
    SecurityDict,
    DatesDict,
    SystemDict,
    total=False,
):
    type: str


class LiqpayRefundDict(TypedDict):
    payment_id: int
    status: FinalStatus
    wait_amount: bool
