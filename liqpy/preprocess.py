from typing import TYPE_CHECKING, Optional
from datetime import timedelta

from .convert import to_datetime, to_milliseconds
from .data import DetailAddenda

if TYPE_CHECKING:
    from json import JSONEncoder
    from .types.request import LiqpayRequestDict


class BasePreprocessor:
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


class Preprocessor(BasePreprocessor):
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

    def date_from(self, value, /, **kwargs):
        return to_milliseconds(value, **kwargs)

    def date_to(self, value, /, **kwargs):
        return to_milliseconds(value, **kwargs)

    def subscribe_date_start(self, value, /, **kwargs):
        return to_datetime(value, **kwargs)

    def letter_of_credit_date(self, value, /, **kwargs):
        return to_datetime(value, **kwargs)

    def expired_date(self, value, /, **kwargs):
        return to_datetime(value, **kwargs)
    
    def verifycode(self, value, /, **kwargs):
        if value:
            return "Y"
    
    def subscribe(self, value, /, **kwargs):
        if value:
            return 1
    
    def letter_of_credit(self, value, /, **kwargs):
        if value:
            return 1
    
    def recurringbytoken(self, value, /, **kwargs):
        if value:
            return "1"
