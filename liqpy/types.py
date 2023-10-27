from typing import TypedDict, Literal, Union
from numbers import Number

from .exceptions import Errcode


Language = Literal["uk", "en"]
SubscribeAction = Literal["subscribe"]

WidgetAction = CheckoutAction = Literal[
    "pay",
    "hold",
    "paysplit",
    "paydonate",
    "auth",
    "letter_of_credit",
    "split_rules",
    "apay",
    "gpay",
]
CallbackAction = Union[
    SubscribeAction, Literal["pay", "hold", "paysplit", "paydonate", "auth", "regular"]
]
SubscriptionAction = Union[SubscribeAction, Literal["unsubscribe", "subscribe_update"]]

SubscribeStatus = Literal["subscribed", "unsubscribed"]
FinalPaymentStatus = Union[
    Literal["error", "failure", "reversed", "success"], SubscribeStatus
]
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
OtherPaymentStatus = Literal[
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
CallbackStatus = Union[FinalPaymentStatus, ConfirmationStatus, OtherPaymentStatus]
MpiEci = Literal[5, 6, 7]
PayType = Literal[
    "card", "liqpay", "privat24", "masterpass", "moment_part", "cash", "invoice", "qr"
]


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
    currency: str
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
    mpi_eci: MpiEci
    order_id: str
    payment_id: Number
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
    status: CallbackStatus
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