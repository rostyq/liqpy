from decimal import Decimal
from typing import Any
from enum import StrEnum, auto
from datetime import datetime
from dataclasses import dataclass, field


class Currency(StrEnum):
    UAH = "UAH"
    USD = "USD"
    EUR = "EUR"


class Action(StrEnum):
    PAY = auto()
    HOLD = auto()
    PAYSPLIT = auto()
    SUBSCRIBE = auto()
    PAYDONATE = auto()
    AUTH = auto()
    REGULAR = auto()


class Status(StrEnum):
    # final payment statuses
    SUCCESS = auto()
    ERROR = auto()
    FAILURE = auto()
    REVERSED = auto()

    # statuses that required payment confirmation
    VERIFY_3DS = "3ds_verify"
    VERIFY_CVV = "cvv_verify"
    VERIFY_OTP = "otp_verify"
    VERIFY_RECEIVER = "receiver_verify"
    VERIFY_SENDER = "sender_verify"

    # other payment statuses
    WAIT_ACCEPT = auto()
    WAIT_SECURE = auto()

    def is_wait(self) -> bool:
        return self in (Status.WAIT_ACCEPT, Status.WAIT_SECURE)

    def requires_confirmation(self) -> bool:
        return self in (
            Status.VERIFY_3DS,
            Status.VERIFY_CVV,
            Status.VERIFY_OTP,
            Status.VERIFY_RECEIVER,
            Status.VERIFY_SENDER,
        )

    def is_final(self) -> bool:
        return self in (
            Status.SUCCESS,
            Status.ERROR,
            Status.FAILURE,
            Status.REVERSED,
        )


class PayWay(StrEnum):
    CARD = auto()
    LIQPAY = auto()
    PRIVAT24 = auto()
    MASTERPASS = auto()
    MOMENT_PART = auto()
    CASH = auto()
    INVOICE = auto()
    QR = auto()


class Code(StrEnum):
    UNKNOWN = auto()

    EXPIRED = auto()

    # financial errors
    E90 = "90"
    E101 = "101"
    E102 = "102"
    E103 = "103"
    E104 = "104"
    E105 = "105"
    E106 = "106"
    E107 = "107"
    E108 = "108"
    E109 = "109"
    E110 = "110"
    E111 = "111"
    E112 = "112"
    E113 = "113"
    E114 = "114"
    E115 = "115"
    E2903 = "2903"
    E2915 = "2915"
    E3914 = "3914"
    E9851 = "9851"
    E9852 = "9852"
    E9854 = "9854"
    E9855 = "9855"
    E9857 = "9857"
    E9859 = "9859"
    E9860 = "9860"
    E9861 = "9861"
    E9863 = "9863"
    E9867 = "9867"
    E9868 = "9868"
    E9872 = "9872"
    E9882 = "9882"
    E9886 = "9886"
    E9961 = "9961"
    E9989 = "9989"

@dataclass(frozen=True, slots=True, eq=False)
class Report:
    id: int = field(repr=True)
    shop_order_id: str = field(repr=True)
    liqpay_order_id: str = field(repr=False)

    amount: Decimal = field(repr=True)
    currency: Currency = field(repr=True)

    sender_commission: Decimal = field(repr=False)
    receiver_commission: Decimal = field(repr=False)
    agent_commission: Decimal = field(repr=False)

    amount_credit: Decimal = field(repr=False)
    comission_credit: Decimal = field(repr=False)
    currency_credit: Decimal = field(repr=False)

    create_date: datetime = field(repr=True)
    end_date: datetime = field(repr=True)

    type: str = field(repr=True)

    status: Status = field(repr=True)
    status_err_code: Code | None = field(repr=False)

    auth_code: Any = field(repr=False)
    description: str = field(repr=False)
    phone: str = field(repr=True)

    sender_country_code: str = field(repr=False)
    card: str = field(repr=False)
    issuer_bank: str = field(repr=False)
    card_country: str = field(repr=False)
    card_type: str = field(repr=False)
    pay_way: PayWay = field(repr=False)

    receiver_card: str = field(repr=False)
    receiver_okpo: int = field(repr=False)

    refund_amount: Decimal | None = field(repr=False)
    refund_date_last: datetime | None = field(repr=False)
    refund_reserve_ids: Any = field(repr=False)

    reserve_refund_id: int | None = field(repr=False)
    reserve_payment_id: int | None = field(repr=False)
    reserve_amount: Decimal | None = field(repr=False)
    reserve_date: datetime | None = field(repr=False)

    completion_date: datetime | None = field(repr=False)
    info: str = field(repr=False)

    compensation_id: str | None = field(repr=False)
    compensation_date: datetime | None = field(repr=False)

    bonusplus_account: str | None = field(repr=False)
    bonus_type: str | None = field(repr=False)
    bonus_percent: Decimal | None = field(repr=False)
    bonus_amount: Decimal | None = field(repr=False)

    def __post_init__(self):
        pass