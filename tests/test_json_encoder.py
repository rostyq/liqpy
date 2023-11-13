from datetime import datetime, date, UTC, timezone, timedelta
from uuid import UUID
from decimal import Decimal

from pytest import fixture

from liqpy.api import Encoder, encode
from liqpy.util import DetailAddenda


@fixture
def encoder():
    return Encoder()


def test_encode_bytes(encoder: Encoder):
    assert encoder.encode(b"") == '""'
    assert encoder.encode(b"test") == '"test"'


def test_encode_date(encoder: Encoder):
    assert encoder.encode(date(2021, 1, 2)) == '"2021-01-02 00:00:00"'


def test_encode_datetime(encoder: Encoder):
    assert (
        encoder.encode(datetime(2021, 1, 2, 3, 4, 5, tzinfo=UTC))
        == '"2021-01-02 03:04:05"'
    )
    assert (
        encoder.encode(
            datetime(2021, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=3)))
        )
        == '"2021-01-02 00:04:05"'
    )
    assert (
        encoder.encode(
            datetime(2021, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=-3)))
        )
        == '"2021-01-02 06:04:05"'
    )


def test_encode_uuid(encoder: Encoder):
    value = "123e4567-e89b-12d3-a456-426614174000"
    assert encoder.encode(UUID(value)) == f'"{value}"'


def test_encode_decimal(encoder: Encoder):
    assert encoder.encode(Decimal(1)) == "1.0"
    assert encoder.encode(Decimal("1.0")) == "1.0"
    assert encoder.encode(Decimal(1.0)) == "1.0"
    assert encoder.encode(Decimal("0.0001")) == "0.0001"


def test_encode_dae(encoder: Encoder):
    dae = DetailAddenda(
        air_line="Avia",
        ticket_number="ACSFD12354SA",
        passenger_name="John Doe",
        flight_number="742",
        origin_city="DP",
        destination_city="NY",
        departure_date=date(2014, 5, 10),
    )
    # TODO: verify
    encoder.encode(dae)
