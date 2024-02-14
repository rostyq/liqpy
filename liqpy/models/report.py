from decimal import Decimal
from typing import Any, Self
from enum import StrEnum, auto, Enum, member
from datetime import datetime
from dataclasses import dataclass

from liqpy.util.convert import to_datetime


class Field(Enum):
    ID = member(lambda x: int(x))
    AMOUNT = member(lambda x: Decimal(x))
    SENDER_COMMISSION = member(lambda x: Decimal(x))
    RECEIVER_COMMISSION = member(lambda x: Decimal(x))
    AGENT_COMMISSION = member(lambda x: Decimal(x))
    CURRENCY = member(lambda x: Currency(x))
    AMOUNT_CREDIT = member(lambda x: Decimal(x) if x else None)
    COMISSION_CREDIT = member(lambda x: Decimal(x) if x else None)
    CURRENCY_CREDIT = member(lambda x: Currency(x) if x else None)
    CREATE_DATE = member(lambda x: to_datetime(x))
    END_DATE = member(lambda x: to_datetime(x))
    TYPE = member(lambda x: x)
    STATUS = member(lambda x: Status(x))
    STATUS_ERR_CODE = member(lambda x: Code(x) if x else None)
    AUTH_CODE = member(lambda x: x if x else None)
    SHOP_ORDER_ID = member(lambda x: x)
    DESCRIPTION = member(lambda x: x)
    PHONE = member(lambda x: x if x else None)
    SENDER_COUNTRY_CODE = member(lambda x: x if x else None)
    CARD = member(lambda x: x)
    ISSUER_BANK = member(lambda x: x)
    CARD_COUNTRY = member(lambda x: x)
    CARD_TYPE = member(lambda x: x)
    PAY_WAY = member(lambda x: PayWay(x))
    RECEIVER_CARD = member(lambda x: x)
    RECEIVER_OKPO = member(lambda x: int(x) if x else None)
    REFUND_AMOUNT = member(lambda x: Decimal(x) if x else None)
    REFUND_DATE_LAST = member(lambda x: to_datetime(x) if x else None)
    REFUND_RESERVE_IDS = member(lambda x: map(lambda v: v.strip(), x.split("|")) if x else [])
    RESERVE_REFUND_ID = member(lambda x: int(x) if x else None)
    RESERVE_PAYMENT_ID = member(lambda x: int(x) if x else None)
    RESERVE_AMOUNT = member(lambda x: Decimal(x) if x else None)
    RESERVE_DATE = member(lambda x: to_datetime(x) if x else None)
    COMPLETION_DATE = member(lambda x: to_datetime(x) if x else None)
    INFO = member(lambda x: x)
    LIQPAY_ORDER_ID = member(lambda x: x if x else None)
    COMPENSATION_ID = member(lambda x: x if x else None)
    COMPENSATION_DATE = member(lambda x: to_datetime(x) if x else None)
    BONUSPLUS_ACCOUNT = member(lambda x: x if x else None)
    BONUS_TYPE = member(lambda x: x if x else None)
    BONUS_PERCENT = member(lambda x: Decimal(x) if x else None)
    BONUS_AMOUNT = member(lambda x: Decimal(x) if x else None)


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

    # subscription statuses
    SUBSCRIBED = auto()
    UNSUBSCRIBED = auto()

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

    # Google Pay
    GPAY = auto()

    # Google Pay Card
    GPAYCARD = auto()

    # Apple Pay
    APAY = auto()


class Code(StrEnum):
    ERR_BLOCKED = auto()
    ERR_CARD_BIN = auto()
    ERR_TOKEN_DECODE = auto()

    # expired codes
    EXPIRED = auto()
    EXPIRED_P24 = auto()
    EXPIRED_3DS = auto()

    MPI = auto()

    E4 = "4"

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
    E9875 = "9875"
    E9882 = "9882"
    E9886 = "9886"
    E9961 = "9961"
    E9989 = "9989"


@dataclass(frozen=True, eq=False, slots=True)
class Report:
    """
    Dataclass model for a LiqPay report comma-separated entry (CSV)
    """

    id: int
    shop_order_id: str
    liqpay_order_id: str

    amount: Decimal
    currency: Currency

    sender_commission: Decimal
    receiver_commission: Decimal
    agent_commission: Decimal

    create_date: datetime
    end_date: datetime

    type: str

    status: Status

    description: str
    phone: str

    sender_country_code: str
    card: str
    issuer_bank: str
    card_country: str
    card_type: str
    pay_way: PayWay

    receiver_card: str
    receiver_okpo: int

    info: str

    amount_credit: Decimal | None = None
    comission_credit: Decimal | None = None
    currency_credit: Currency | None = None

    auth_code: str | None = None

    status_err_code: Code | None = None

    refund_amount: Decimal | None = None
    refund_date_last: datetime | None = None
    refund_reserve_ids: list[str] = []

    reserve_refund_id: int | None = None
    reserve_payment_id: int | None = None
    reserve_amount: Decimal | None = None
    reserve_date: datetime | None = None

    completion_date: datetime | None = None

    compensation_id: str | None = None
    compensation_date: datetime | None = None

    bonusplus_account: str | None = None
    bonus_type: str | None = None
    bonus_percent: Decimal | None = None
    bonus_amount: Decimal | None = None

    @classmethod
    def from_dict(cls: Self, data: dict[str, str]) -> Self:
        """
        Create a new instance from a dictionary of strings

        Useful
        """
        return cls(**{k.lower(): Field[k].value(v) for k, v in data.items()})
