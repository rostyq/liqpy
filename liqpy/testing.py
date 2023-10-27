from typing import Literal as Literal, Optional
from enum import Enum as Enum


__all__ = ["TestCard"]


class TestCard(Enum):
    SUCCESSFUL_PAYMENT = "4242424242424242"
    SUCCESSFUL_PAYMENT_WITH_3DS = "4000000000003063"
    SUCCESSFUL_PAYMENT_WITH_OTP = "4000000000003089"
    SUCCESSFUL_PAYMENT_WITH_CVV = "4000000000003055"

    FAILURE_PAYMENT_ERRCODE_LIMIT = "4000000000000002"
    FAILURE_PAYMENT_ERRCODE_9859 = "4000000000009995"

    SUCCESSFUL_PAYMENT_WITH_TOKEN = "sandbox_token"

    @classmethod
    def successful(cls, code: Optional[Literal["3ds", "otp", "cvv", "token"]] = None):
        if code is None:
            return cls.SUCCESSFUL_PAYMENT.value
        else:
            return cls[f"SUCCESSFUL_PAYMENT_WITH_{code.upper()}"].value

    @classmethod
    def failure(cls, errcode: Literal["limit", "9859"] = "limit"):
        return cls[f"FAILURE_PAYMENT_ERRCODE_{errcode.upper()}"].value
