from typing import Literal


Language = Literal["uk", "en"]
Currency = Literal["UAH", "USD", "EUR"]
Format = Literal["json", "xml", "csv"]

PayType = Literal[
    "apay",
    "gpay",
    "apay_tavv",
    "gpay_tavv",
    "tavv",
]
PayOption = Literal[
    "card", "liqpay", "privat24", "masterpass", "moment_part", "cash", "invoice", "qr"
]
SubscribePeriodicity = Literal["month", "year"]
