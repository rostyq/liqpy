from typing import Literal as Literal, Optional
from enum import Enum as Enum
from datetime import date, timedelta
from random import randint


__all__ = ["TestCard", "gen_card_expire", "gen_card_cvv", "fmt_card_expire_date"]


def fmt_card_expire_date(value: date) -> tuple[str, str]:
    """Format a date object to MM, YY strings"""
    return str(value.month).rjust(2, "0"), str(value.year)[-2:].rjust(2, "0")


def gen_card_expire(valid: bool = True):
    """Generate a random card expiration date"""
    d = date.today()

    if valid:
        d += timedelta(days=randint(1, 365 * 4))
    else:
        d -= timedelta(days=randint(1, 30 * 3))

    return fmt_card_expire_date(d)


def gen_card_cvv() -> str:
    """Generate a random CVV code"""
    return str(randint(0, 999)).rjust(3, "0")


class TestCard(Enum):
    """
    Test card numbers for LiqPay API requests

    [LiqPay API Testing](https://www.liqpay.ua/en/documentation/api/sandbox)
    """

    SUCCESSFUL_PAYMENT = "4242424242424242"
    SUCCESSFUL_PAYMENT_WITH_3DS = "4000000000003063"
    SUCCESSFUL_PAYMENT_WITH_OTP = "4000000000003089"
    SUCCESSFUL_PAYMENT_WITH_CVV = "4000000000003055"

    FAILURE_PAYMENT_ERRCODE_LIMIT = "4000000000000002"
    FAILURE_PAYMENT_ERRCODE_9859 = "4000000000009995"

    SUCCESSFUL_PAYMENT_WITH_TOKEN = "sandbox_token"

    @classmethod
    def successful(cls, code: Optional[Literal["3ds", "otp", "cvv", "token"]] = None):
        """Card number for a successful payment with a specific code"""
        if code is None:
            return cls.SUCCESSFUL_PAYMENT.value
        else:
            return cls[f"SUCCESSFUL_PAYMENT_WITH_{code.upper()}"].value

    @classmethod
    def failure(cls, errcode: Literal["limit", "9859"] = "limit"):
        """Card number for a failed payment with a specific error code"""
        return cls[f"FAILURE_PAYMENT_ERRCODE_{errcode.upper()}"].value
