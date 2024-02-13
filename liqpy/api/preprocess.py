from typing import TYPE_CHECKING, Optional

from liqpy.models.request import DetailAddenda
from liqpy.util.convert import to_datetime, to_milliseconds

if TYPE_CHECKING:
    from json import JSONEncoder

    from liqpy.types.request import LiqpayRequestDict


class BasePreprocessor:
    """Base class for LiqPay API request preprocessor"""
    def __call__(
        self, o: "LiqpayRequestDict", /, encoder: Optional["JSONEncoder"], **kwargs
    ):
        if encoder is None:
            encoder = JSONEncoder()

        for key, value in o.items():
            try:
                fn = getattr(self, key, None)

                if not callable(fn):
                    continue

                processed = fn(value, encoder=encoder, **kwargs.get(key, {}))

                if processed is not None:
                    o[key] = processed

            except Exception as e:
                raise Exception(f"Failed to convert {key} parameter.") from e


def to_one(value, **kwargs):
    if value:
        return 1


class Preprocessor(BasePreprocessor):
    """LiqPay API request preprocessor"""

    def __init__(self) -> None:
        super().__init__()
        self.date_from = to_milliseconds
        self.date_to = to_milliseconds
        self.expired_date = to_datetime
        self.subscribe_date_start = to_datetime
        self.letter_of_credit_date = to_datetime
        self.subscribe = to_one
        self.letter_of_credit = to_one
        self.recurringbytoken = to_one

    def dae(self, value, /, **kwargs):
        if isinstance(value, DetailAddenda):
            return value
        else:
            return DetailAddenda(**value)

    def split_rules(self, value, /, encoder: "JSONEncoder", **kwargs):
        if isinstance(value, list):
            return encoder.encode(value)

    def paytypes(self, value, /, **kwargs):
        if isinstance(value, list):
            return ",".join(value)

    def verifycode(self, value, /, **kwargs):
        if value:
            return "Y"
    