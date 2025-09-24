from typing import Any, Callable, AnyStr, TYPE_CHECKING, cast
from json import JSONDecoder
from ipaddress import IPv4Address
from base64 import b64decode
from secrets import compare_digest
from decimal import Decimal

from liqpy.api import sign
from liqpy.api.exceptions import LiqPayRequestException
from liqpy import datetime_from_millis, noop

if TYPE_CHECKING:
    from liqpy.types.response import LiqpayCallbackDict


class LiqpayDecoder(JSONDecoder):
    """Custom JSON decoder for LiqPay API responses"""

    def __init__(self):
        super().__init__(
            object_hook=None,
            parse_float=str,
            parse_int=int,
            parse_constant=None,
            strict=True,
            object_pairs_hook=self._object_pairs_hook,
        )
        self.default: dict[str, Callable[[Any], Any]] = {
            "mpi_eci": int,
            "ip": IPv4Address,
            "agent_commission": Decimal,
            "amount": Decimal,
            "amount_bonus": Decimal,
            "amount_credit": Decimal,
            "amount_debit": Decimal,
            "commission_credit": Decimal,
            "commission_debit": Decimal,
            "receiver_commission": Decimal,
            "sender_bonus": Decimal,
            "sender_commission": Decimal,
            "refund_amount": Decimal,
            "create_date": datetime_from_millis,
            "end_date": datetime_from_millis,
            "reserve_date": datetime_from_millis,
            "completion_date": datetime_from_millis,
            "refund_date_last": datetime_from_millis,
            "wait_reserve_status": lambda v: cast(str, v).lower() == "true",
        }

    def __call__(self, s: AnyStr) -> "LiqpayCallbackDict":
        return self.decode(b64decode(s).decode())

    def callback(
        self, data: bytes, /, signature: bytes, private_key: bytes
    ) -> "LiqpayCallbackDict":
        if compare_digest(sign(data, private_key), signature):
            return self(data)
        else:
            raise LiqPayRequestException(
                "invalid_signature",
                details={"data": self(data), "signature": signature},
            )

    def _object_pairs_hook(self, items: list[tuple[str, Any]], /) -> dict[str, Any]:
        result, errors = {}, []
        for key, value in items:
            if value is None:
                continue
            try:
                value = self.default.get(key, noop)(value)
                if value is not None:
                    result[key] = value
            except (TypeError, ValueError) as e:
                e.add_note(f"Error processing key '{key}' with value '{value}': {e}")
                errors.append(e)

        if len(errors) == 0:
            return result
        else:
            raise ExceptionGroup(
                "Errors occurred during decoding LiqPay response payload", errors
            )
