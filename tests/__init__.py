from typing import TYPE_CHECKING
from pytest import fixture

if TYPE_CHECKING:
    from liqpy.api.validation import LiqpayValidator


__all__ = ("encoder", "decoder", "validator")


@fixture
def decoder():
    from liqpy.api.decoder import LiqpayDecoder

    return LiqpayDecoder()


@fixture
def validator():
    from liqpy.api.validation import LiqpayValidator

    return LiqpayValidator()


@fixture
def encoder(validator: "LiqpayValidator"):
    from liqpy.api.encoder import LiqpayEncoder

    return LiqpayEncoder(validator, sort_keys=False)
