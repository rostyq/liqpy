from typing import TYPE_CHECKING, Optional
from json import JSONEncoder

from liqpy.models.request import DetailAddenda
from liqpy.util.convert import to_datetime, to_milliseconds

if TYPE_CHECKING:
    from liqpy.types.request import LiqpayRequestDict


class BasePreprocessor:
    """Base class for LiqPay API request preprocessor"""
    def __call__(
        self, o: "LiqpayRequestDict", /, encoder: Optional["JSONEncoder"] = None, **kwargs
    ):
        if encoder is None:
            encoder = JSONEncoder()

        for key, value in o.items():
            try:
                fn = getattr(self, key, None)

                if not callable(fn):
                    continue

                o[key] = fn(value, encoder=encoder, **kwargs.get(key, {}))

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
        elif isinstance(value, dict):
            return DetailAddenda.from_json(value)
        elif isinstance(value, str):
            return value
        else:
            raise TypeError("Invalid dae value type.")

    def split_rules(self, value, /, encoder: "JSONEncoder", **kwargs):
        if isinstance(value, list):
            return encoder.encode(value)
        elif isinstance(value, str):
            return value
        else:
            raise TypeError("Invalid split_rules value type.")

    def paytypes(self, value, /, **kwargs):
        if isinstance(value, list):
            return ",".join(value)
        elif isinstance(value, str):
            return value
        else:
            raise TypeError("Invalid paytypes value type.")

    def verifycode(self, value, /, **kwargs):
        if value:
            return "Y"
    