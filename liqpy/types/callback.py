from typing import Literal, TypedDict

from numbers import Number
from datetime import datetime
from ipaddress import IPv4Address

from liqpy.types import status
from liqpy.types.error import LiqPayErrcode
from liqpy.types.common import Currency, PayType, Language


CallbackAction = Literal[
    "pay", "hold", "paysplit", "subscribe", "paydonate", "auth", "regular"
]
ThreeDS = Literal[5, 6, 7]


class LiqpayCallbackDict(TypedDict, total=False):
    acq_id: Number
    action: CallbackAction
    agent_commission: Number
    amount: Number
    amount_bonus: Number
    amount_credit: Number
    amount_debit: Number
    authcode_credit: str
    authcode_debit: str
    card_token: str
    commission_credit: Number
    commission_debit: Number
    completion_date: datetime
    create_date: datetime
    currency: Currency
    currency_credit: str
    currency_debit: str
    customer: str
    description: str
    end_date: datetime
    err_code: LiqPayErrcode
    err_description: str
    info: str
    ip: IPv4Address
    is_3ds: bool
    language: Language
    liqpay_order_id: str
    mpi_eci: ThreeDS
    order_id: str
    payment_id: int
    paytype: PayType
    public_key: str
    receiver_commission: Number
    redirect_to: str
    refund_date_last: datetime
    rrn_credit: str
    rrn_debit: str
    sender_bonus: Number
    sender_card_bank: str
    sender_card_country: str
    sender_card_mask2: str
    sender_card_type: str
    sender_commission: Number
    sender_first_name: str
    sender_last_name: str
    sender_phone: str
    status: status.CallbackStatus
    token: str
    type: str
    version: Literal[3]
    err_erc: LiqPayErrcode
    product_category: str
    product_description: str
    product_name: str
    product_url: str
    refund_amount: Number
    verifycode: str


class LiqpayRefundDict(TypedDict, total=False):
    payment_id: int
    status: status.FinalStatus
    wait_amount: bool
