from datetime import datetime, date, UTC, timezone, timedelta
from uuid import UUID
from decimal import Decimal
from json import loads, dumps
from base64 import b64decode
from urllib.parse import parse_qs
from unittest.mock import patch

from pytest import mark

from . import *


@mark.parametrize("data", [b"", b"test"])
def test_encode_bytes(encoder, data):
    assert encoder.encode(data) == dumps(data.decode())


@mark.parametrize("value,expected", [(date(2021, 1, 2), '"2021-01-02 00:00:00"')])
def test_encode_date(encoder, value, expected):
    assert encoder.encode(value) == expected


@mark.parametrize(
    "value,expected",
    [
        (datetime(2021, 1, 2, 5, 4, 5, tzinfo=UTC), '"2021-01-02 05:04:05"'),
        (
            datetime(2021, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=3))),
            '"2021-01-02 00:04:05"',
        ),
        (
            datetime(2021, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=-3))),
            '"2021-01-02 06:04:05"',
        ),
    ],
)
def test_encode_datetime(encoder, value, expected):
    assert encoder.encode(value) == expected


@mark.parametrize("value", ["123e4567-e89b-12d3-a456-426614174000"])
def test_encode_uuid(encoder, value):
    assert encoder.encode(UUID(value)) == f'"{value}"'


@mark.parametrize(
    "value,expected", [(1, "1"), ("1.0", "1"), (1.0, "1"), ("0.0001", "0.0001")]
)
def test_encode_decimal(encoder, value, expected):
    assert encoder.encode(Decimal(value)) == expected


@mark.parametrize(
    "data",
    [
        {
            "airLine": "Avia",
            "ticketNumber": "ACSFD12354SA",
            "passengerName": "John Doe",
            "flightNumber": "742",
            "originCity": "DP",
            "destinationCity": "NY",
            "departureDate": "100514",
        }
    ],
)
def test_encode_dae(encoder, data):
    from liqpy.models.request import DetailAddenda

    dae = DetailAddenda.from_dict(data)

    assert loads(b64decode(encoder.encode(dae).encode()).decode()) == data


@mark.parametrize(
    "payload,data,signature",
    [
        (
            {
                "version": 3,
                "action": "pay",
                "amount": Decimal(1),
                "currency": "USD",
                "description": "description text",
                "order_id": "order_id_1",
            },
            "eyAidmVyc2lvbiIgOiAzLCAicHVibGljX2tleSIgOiAieW91cl9wdWJsaWNfa2V5IiwgImFjdGlvbiIgOiAicGF5IiwgImFtb3VudCIgOiAxLCAiY3VycmVuY3kiIDogIlVTRCIsICJkZXNjcmlwdGlvbiIgOiAiZGVzY3JpcHRpb24gdGV4dCIsICJvcmRlcl9pZCIgOiAib3JkZXJfaWRfMSIgfQ==",
            "QvJD5u9Fg55PCx/Hdz6lzWtYwcI=",
        ),
    ],
)
def test_checkout_example(monkeypatch, encoder, payload, data, signature):
    # Patch encoder to match official documentation formatting
    monkeypatch.setattr(
        encoder,
        "encode",
        lambda obj: encoder.__class__.encode(encoder, obj)
        .replace(",", ", ")
        .replace(":", " : ")
        .replace("{", "{ ")
        .replace("}", " }"),
    )
    
    # Patch the sign function to add newlines to base64 data like official docs
    from liqpy.api import sign as original_sign
    def patched_sign(data: bytes, key: bytes) -> bytes:
        # Add newlines to base64 data every 76 characters (like bash base64 command)
        data_str = data.decode()
        data_with_newlines = '\n'.join(data_str[i:i+76] for i in range(0, len(data_str), 76))
        return original_sign(data_with_newlines.encode(), key)
    
    monkeypatch.setattr("liqpy.api.encoder.sign", patched_sign)
    
    result = encoder(
        payload.pop("action"),
        payload.pop("version"),
        public_key="your_public_key",
        private_key=b"your_private_key",
        **payload,
    )
    qs = parse_qs(result.decode())
    assert qs["data"][0] == data
    assert qs["signature"][0] == signature
