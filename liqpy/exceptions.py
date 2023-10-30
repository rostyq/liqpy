from typing import Literal, TYPE_CHECKING, Optional, Union
from typing import get_args

if TYPE_CHECKING:
    from requests import Response


UNKNOWN_ERRCODE = "unknown"
UNKNOWN_ERRMSG = "Unknown error"


def is_exception(
    action: str,
    result: Literal["error", "ok"],
    status: Literal["error", "failure", "success"],
) -> bool:
    if result == "error" or status in ["error", "failure"]:
        if action != "status" or status == "error":
            return True
    return False


class LiqPayException(Exception):
    code: str
    details: dict
    response: Optional["Response"] = None

    def __init__(
        self,
        /,
        code: str | None = None,
        description: str | None = None,
        *,
        response: Optional["Response"] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(description or UNKNOWN_ERRMSG)
        self.code = code or UNKNOWN_ERRCODE
        self.response = response
        self.details = details


LiqpayAntiFraudErrcode = Literal["limit", "frod", "decline"]


LiqpayNonFinancialErrcode = Literal[
    "err_auth",
    "err_cache",
    "user_not_found",
    "err_sms_send",
    "err_sms_otp",
    "shop_blocked",
    "shop_not_active",
    "invalid_signature",
    "order_id_empty",
    "err_shop_not_agent",
    "err_card_def_notfound",
    "err_no_card_token",
    "err_card_liqpay_def",
    "err_card_type",
    "err_card_country",
    "err_limit_amount",
    "err_payment_amount_limit",
    "amount_limit",
    "payment_err_sender_card",
    "payment_processing",
    "err_payment_discount",
    "err_wallet",
    "err_get_verify_code",
    "err_verify_code",
    "wait_info",
    "err_path",
    "err_payment_cash_acq",
    "err_split_amount",
    "err_card_receiver_def",
    "payment_err_status",
    "public_key_not_found",
    "payment_not_found",
    "payment_not_subscribed",
    "wrong_amount_currency",
    "err_amount_hold",
    "err_access",
    "order_id_duplicate",
    "err_blocked",
    "err_empty",
    "err_empty_phone",
    "err_missing",
    "err_wrong",
    "err_wrong_currency",
    "err_phone",
    "err_card",
    "err_card_bin",
    "err_terminal_notfound",
    "err_commission_notfound",
    "err_payment_create",
    "err_mpi",
    "err_currency_is_not_allowed",
    "err_look",
    "err_mods_empty",
    "payment_err_type",
    "err_payment_currency",
    "err_payment_exchangerates",
    "err_signature",
    "err_api_action",
    "err_api_callback",
    "err_api_ip",
    "expired_phone",
    "expired_3ds",
    "expired_otp",
    "expired_cvv",
    "expired_p24",
    "expired_sender",
    "expired_pin",
    "expired_ivr",
    "expired_captcha",
    "expired_password",
    "expired_senderapp",
    "expired_prepared",
    "expired_mp",
    "expired_qr",
    "5",
]

LiqpayFinancialErrcode = Literal[
    "90",
    "101",
    "102",
    "103",
    "104",
    "105",
    "106",
    "107",
    "108",
    "109",
    "110",
    "111",
    "112",
    "113",
    "114",
    "115",
    "2903",
    "2915",
    "3914",
    "9851",
    "9852",
    "9854",
    "9855",
    "9857",
    "9859",
    "9860",
    "9861",
    "9863",
    "9867",
    "9868",
    "9872",
    "9882",
    "9886",
    "9961",
    "9989",
]

Errcode = Union[
    LiqpayAntiFraudErrcode,
    LiqpayFinancialErrcode,
    LiqpayNonFinancialErrcode,
]


class LiqPayAntiFraudException(LiqPayException):
    code: LiqpayAntiFraudErrcode


class LiqPayNonFinancialException(LiqPayException):
    code: LiqpayNonFinancialErrcode


class LiqPayFinancialException(LiqPayException):
    code: LiqpayFinancialErrcode


def get_exception_cls(code: str | None = None) -> type[LiqPayException]:
    if code in get_args(LiqpayAntiFraudErrcode):
        return LiqPayAntiFraudException
    elif code in get_args(LiqpayFinancialErrcode):
        return LiqPayFinancialException
    elif code in get_args(LiqpayNonFinancialErrcode):
        return LiqPayNonFinancialException
    else:
        return LiqPayException


def exception_factory(
    code: str | None = None,
    description: str | None = None,
    *,
    response: Optional["Response"] = None,
    details: Optional[dict] = None,
) -> LiqPayException:
    cls = get_exception_cls(code)
    return cls(code, description, response=response, details=details)
