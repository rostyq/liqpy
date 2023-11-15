from typing import Literal as _Literal, Union as _Union


SubscriptionStatus = _Literal["subscribed", "unsubscribed"]
ErrorStatus = _Literal["error", "failure"]
SuccessStatus = _Literal["success"]
FinalStatus = _Union[ErrorStatus, _Literal["reversed"], SuccessStatus]
ConfirmationStatus = _Literal[
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
OtherStatus = _Literal[
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
Status = CallbackStatus = _Union[
    SubscriptionStatus, FinalStatus, ConfirmationStatus, OtherStatus
]
