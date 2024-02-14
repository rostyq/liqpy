from pandas import (
    read_csv as pd_read_csv,
    UInt64Dtype,
    Float64Dtype,
    CategoricalDtype,
    StringDtype,
    DataFrame,
)

from liqpy.models.report import Currency, Status, Action, Code, PayWay

ID_TYPE = UInt64Dtype()
STRING_TYPE = StringDtype()
FLOAT_TYPE = Float64Dtype()

CURRENCY_TYPE = CategoricalDtype(categories=Currency._member_map_.values())
ACTION_TYPE = CategoricalDtype(categories=Action._member_map_.values())

STATUS_TYPE = CategoricalDtype(categories=Status._member_map_.values())
CODE_TYPE = CategoricalDtype(categories=Code._member_map_.values())
PAYWAY_TYPE = CategoricalDtype(categories=PayWay._member_map_.values())

COLUMN_TYPES = {
    "ID": ID_TYPE,
    "AMOUNT": FLOAT_TYPE,
    "SENDER_COMMISSION": FLOAT_TYPE,
    "RECEIVER_COMMISSION": FLOAT_TYPE,
    "AGENT_COMMISSION": FLOAT_TYPE,
    "CURRENCY": CURRENCY_TYPE,
    "AMOUNT_CREDIT": FLOAT_TYPE,
    "COMISSION_CREDIT": FLOAT_TYPE,
    "CURRENCY_CREDIT": CURRENCY_TYPE,
    "CREATE_DATE": STRING_TYPE,
    "END_DATE": STRING_TYPE,
    "TYPE": STRING_TYPE,
    "STATUS": STATUS_TYPE,
    "STATUS_ERR_CODE": CODE_TYPE,
    "AUTH_CODE": STRING_TYPE,
    "SHOP_ORDER_ID": STRING_TYPE,
    "DESCRIPTION": STRING_TYPE,
    "PHONE": STRING_TYPE,
    "SENDER_COUNTRY_CODE": STRING_TYPE,
    "CARD": STRING_TYPE,
    "ISSUER_BANK": STRING_TYPE,
    "CARD_COUNTRY": STRING_TYPE,
    "CARD_TYPE": STRING_TYPE,
    "PAY_WAY": PAYWAY_TYPE,
    "RECEIVER_CARD": STRING_TYPE,
    "RECEIVER_OKPO": ID_TYPE,
    "REFUND_AMOUNT": FLOAT_TYPE,
    "REFUND_DATE_LAST": STRING_TYPE,
    "REFUND_RESERVE_IDS": STRING_TYPE,
    "RESERVE_REFUND_ID": ID_TYPE,
    "RESERVE_PAYMENT_ID": ID_TYPE,
    "RESERVE_AMOUNT": FLOAT_TYPE,
    "RESERVE_DATE": STRING_TYPE,
    "COMPLETION_DATE": STRING_TYPE,
    "INFO": STRING_TYPE,
    "LIQPAY_ORDER_ID": STRING_TYPE,
    "COMPENSATION_ID": ID_TYPE,
    "COMPENSATION_DATE": STRING_TYPE,
    "BONUSPLUS_ACCOUNT": STRING_TYPE,
    "BONUS_TYPE": STRING_TYPE,
    "BONUS_PERCENT": FLOAT_TYPE,
    "BONUS_AMOUNT": FLOAT_TYPE,
}

DATE_COLUMNS = [key for key in COLUMN_TYPES.keys() if "_DATE" in key]

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def read_liqpay_csv(source, **kwargs) -> DataFrame:
    """
    Read a CSV file from LiqPay with the appropriate column types

    Arguments
    ---------

    - `source`: File path or file-like object
    - `**kwargs`: Additional arguments to pass to `pandas.read_csv`
    """
    return pd_read_csv(
        source,
        encoding="utf-16",
        dtype=COLUMN_TYPES,
        parse_dates=DATE_COLUMNS,
        date_format=DATE_FORMAT,
        index_col="ID",
        **kwargs,
    )
