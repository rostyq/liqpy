from typing import Literal as _Literal

Language = _Literal["uk", "en"]
Currency = _Literal["UAH", "USD", "EUR"]
Format = _Literal["json", "xml", "csv"]

PayType = _Literal[
    "apay",
    "gpay",
    "apay_tavv",
    "gpay_tavv",
    "tavv",
]
PayOption = _Literal[
    "card", "liqpay", "privat24", "masterpass", "moment_part", "cash", "invoice", "qr"
]
SubscribePeriodicity = _Literal["month", "year"]
