from typing import TYPE_CHECKING
from functools import singledispatchmethod
from base64 import b64encode
from urllib.parse import urlencode
from json import JSONEncoder
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime, UTC
from ipaddress import IPv4Address

from liqpy.models.request import FiscalInfo, DetailAddenda, SplitRules, PayTypes
from liqpy.api import DATE_FMT, sign

if TYPE_CHECKING:
    from liqpy.api.validation import LiqpayValidator
    from liqpy.types.request import LiqpayRequest


__all__ = ("LiqpayEncoder", "JSONEncoder", "SEPARATORS", "ReportEncoder")


SEP = ","
SEPARATORS = (SEP, ":")


class LiqpayEncoder(JSONEncoder):
    """Custom JSON encoder for LiqPay API requests"""

    date_fmt = DATE_FMT

    tz = UTC

    def __init__(
        self,
        validator: "LiqpayValidator",
        *,
        sort_keys: bool = True,
        separators: tuple[str, str] = SEPARATORS,
    ):
        super().__init__(
            skipkeys=False,
            ensure_ascii=False,
            check_circular=True,
            allow_nan=False,
            sort_keys=sort_keys,
            indent=None,
            separators=separators,
            default=None,
        )
        self.validator = validator

    def __call__(self, request: "LiqpayRequest", /) -> bytes:
        """Validate and encode LiqpayRequest to Base 64 JSON."""
        return b64encode(self.encode(self.validator(request)).encode())

    def form(self, pk: bytes, req: "LiqpayRequest") -> tuple[bytes, bytes]:
        """
        Encode parameters and sign them using private key.
        Returns a tuple of bytes `(data, signature)`.
        """
        return (data := self(req)), sign(data, pk)

    def payload(self, private_key: bytes, request: "LiqpayRequest") -> bytes:
        """Prepare URL-encoded payload for HTTP request."""
        data, signature = self.form(private_key, request)
        return urlencode({"data": data, "signature": signature}).encode()

    @singledispatchmethod
    def default(self, o):
        return super().default(o)

    @default.register
    def _(self, o: Decimal) -> float | int:
        n, d = o.as_integer_ratio()
        return n if d == 1 else float(o)

    @default.register
    def _(self, o: datetime) -> str:
        return o.astimezone(self.tz).strftime(self.date_fmt)

    @default.register
    def _(self, o: date) -> str:
        return o.strftime(self.date_fmt)

    @default.register
    def _(self, o: bytes) -> str:
        return o.decode("utf-8")

    @default.register
    def _(self, o: UUID) -> str:
        return str(o)

    @default.register
    def _(self, o: DetailAddenda):
        json = super().encode(o.to_dict())
        return b64encode(json.encode()).decode()

    @default.register
    def _(self, o: SplitRules):
        return super().encode(o.to_list())

    @default.register
    def _(self, o: FiscalInfo):
        return o.to_dict()

    @default.register
    def _(self, o: PayTypes):
        return SEP.join(o)

    @default.register
    def _(self, o: IPv4Address) -> str:
        return str(o)


class ReportEncoder(JSONEncoder):
    """Custom JSON encoder for LiqPay API reports"""

    def __init__(
        self,
        *,
        sort_keys: bool = True,
        separators: tuple[str, str] = SEPARATORS,
    ):
        super().__init__(
            skipkeys=False,
            ensure_ascii=False,
            check_circular=True,
            allow_nan=False,
            sort_keys=sort_keys,
            indent=None,
            separators=separators,
            default=None,
        )

    @singledispatchmethod
    def default(self, o):
        return super().default(o)

    @default.register
    def _(self, o: Decimal) -> float | int:
        n, d = o.as_integer_ratio()
        return n if d == 1 else float(o)

    @default.register
    def _(self, o: datetime) -> str:
        return o.isoformat()

    @default.register
    def _(self, o: IPv4Address) -> str:
        return str(o)
