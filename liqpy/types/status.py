from typing import Literal as _L, Union as _U


subscribe = _L["subscribed", "unsubscribed"]
final = _U[_L["error", "failure", "reversed", "success"], subscribe]
confirmation = _L[
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
other = _L[
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

callback = _U[final, confirmation, other]
