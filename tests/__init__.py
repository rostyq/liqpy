from pytest import fixture

__all__ = ("encoder", "decoder", "validator")


@fixture
def decoder():
    from liqpy.api.decoder import LiqpayDecoder

    return LiqpayDecoder()


@fixture
def validator():
    from liqpy.api.validation import LiqpayValidator

    return LiqpayValidator()


@fixture()
def encoder(validator, request):
    from liqpy.api.encoder import LiqpayEncoder

    return LiqpayEncoder(validator, **getattr(request, "param", {}))
