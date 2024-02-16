from zoneinfo import ZoneInfo


__all__ = ("LIQPAY_TZ", "URL", "VERSION", "DATE_FORMAT")


URL = "https://www.liqpay.ua"
VERSION = 3

LIQPAY_TZ = ZoneInfo("Europe/Kyiv")

DATE_FORMAT = r"%Y-%m-%d %H:%M:%S"
