from os import getenv
from pytest import fixture, FixtureRequest

__all__ = (
    "encoder",
    "decoder",
    "validator",
    "base_client",
    "sync_client",
    "async_client",
    "public_key",
    "private_key",
    "response",
)


@fixture(scope="session")
def decoder():
    from liqpy.api.decoder import LiqpayDecoder

    return LiqpayDecoder()


@fixture(scope="session")
def validator():
    from liqpy.api.validation import LiqpayValidator

    return LiqpayValidator()


@fixture
def encoder(validator, request):
    from liqpy.api.encoder import LiqpayEncoder

    return LiqpayEncoder(validator, **getattr(request, "param", {}))


@fixture
def public_key(request: FixtureRequest) -> str:
    return (
        getattr(request, "param", None)
        or getattr(request.config.option, "public_key", None)
        or getenv("LIQPAY_PUBLIC_KEY")
        or "your_public_key"
    )


@fixture
def private_key(request: FixtureRequest) -> str:
    return (
        getattr(request, "param", None)
        or getattr(request.config.option, "private_key", None)
        or getenv("LIQPAY_PUBLIC_KEY")
        or "your_private_key"
    )


@fixture
def base_client(encoder, decoder, public_key, private_key):
    from liqpy.client import BaseClient

    return BaseClient(public_key, private_key, encoder=encoder, decoder=decoder)


@fixture(scope="session")
def sync_client(encoder, decoder, public_key, private_key):
    from liqpy.client import Client

    with Client(
        public_key,
        private_key,
        encoder=encoder,
        decoder=decoder,
    ) as client:
        yield client


@fixture(scope="session")
async def async_client(encoder, decoder, public_key, private_key):
    from liqpy.client import AsyncClient

    async with AsyncClient(
        public_key,
        private_key,
        encoder=encoder,
        decoder=decoder,
    ) as client:
        yield client


@fixture
def response(request):
    from httpx import Response, Request

    params = getattr(request, "param", {})
    headers: dict[str, str] = params.get("headers", {})
    response = Response(
        params.get("status_code", 200),
        content=params.get("content", None),
        text=params.get("text", None),
        json=params.get("json", None),
        headers=headers if headers else None,
    )
    if location := headers.get("Location"):
        response.next_request = Request("GET", location)

    return response
