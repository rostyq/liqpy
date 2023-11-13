from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from requests import Response

    from liqpy.types.error import (
        LiqPayErrcode,
        LiqpayAntiFraudErrcode,
        LiqpayFinancialErrcode,
        LiqpayNonFinancialErrcode,
        LiqpayExpireErrcode,
        LiqpayRequestErrcode,
        LiqpayPaymentErrcode,
    )


UNKNOWN_ERRCODE = "unknown"
UNKNOWN_ERRMSG = "Unknown error"

TRANSLATIONS = {
    "Платеж не найден": "Payment not found",
}


class LiqPayException(Exception):
    code: "LiqPayErrcode"
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
        description = TRANSLATIONS.get(description, description)

        super().__init__(description or UNKNOWN_ERRMSG)
        self.code = code or UNKNOWN_ERRCODE
        self.response = response
        self.details = details


class LiqPayAntiFraudException(LiqPayException):
    code: "LiqpayAntiFraudErrcode"


class LiqPayNonFinancialException(LiqPayException):
    code: "LiqpayNonFinancialErrcode"


class LiqPayExpireException(LiqPayNonFinancialException):
    code: "LiqpayExpireErrcode"


class LiqPayRequestException(LiqPayNonFinancialException):
    code: "LiqpayRequestErrcode"


class LiqPayPaymentException(LiqPayNonFinancialException):
    code: "LiqpayPaymentErrcode"


class LiqPayFinancialException(LiqPayException):
    code: "LiqpayFinancialErrcode"


def get_exception_cls(code: str | None = None) -> type[LiqPayException]:
    if code is None or code == "unknown":
        return LiqPayException
    elif code in ("limit", "frod", "decline"):
        return LiqPayAntiFraudException
    elif code.isdigit() and code != "5":
        return LiqPayFinancialException
    elif code.startswith("expired_"):
        return LiqPayExpireException
    elif code.startswith("err_"):
        return LiqPayNonFinancialException
    elif code.startswith(("shop_")):
        return LiqPayNonFinancialException
    elif code.endswith(("_not_found", "_limit")):
        return LiqPayNonFinancialException
    elif code.startswith("payment_"):
        return LiqPayExpireException
    elif code in (
        "invalid_signature",
        "public_key_not_found",
        "order_id_empty",
        "amount_limit",
        "wrong_amount_currency",
    ):
        return LiqPayRequestException
    else:
        return LiqPayException


def exception(
    code: str | None = None,
    description: str | None = None,
    *,
    response: Optional["Response"] = None,
    details: Optional[dict] = None,
) -> LiqPayException:
    cls = get_exception_cls(code)
    return cls(code, description, response=response, details=details)
