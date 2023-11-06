from typing import Literal, TypedDict

from numbers import Number

from liqpy.exceptions import Errcode
from liqpy.types import status
from liqpy.types.acquring import Currency, PayType


CallbackAction = Literal[
    "pay", "hold", "paysplit", "subscribe", "paydonate", "auth", "regular"
]
ThreeDS = Literal[5, 6, 7]


class CallbackDict(TypedDict, total=False):
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
    completion_date: str
    create_date: str
    currency: Currency
    currency_credit: str
    currency_debit: str
    customer: str
    description: str
    end_date: str
    err_code: Errcode
    err_description: str
    info: str
    ip: str
    is_3ds: bool
    liqpay_order_id: str
    mpi_eci: ThreeDS
    order_id: str
    payment_id: int
    paytype: PayType
    public_key: str
    receiver_commission: Number
    redirect_to: str
    refund_date_last: str
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
    status: status.callback
    token: str
    type: str
    version: Literal[3]
    err_erc: Errcode
    product_category: str
    product_description: str
    product_name: str
    product_url: str
    refund_amount: Number
    verifycode: str
