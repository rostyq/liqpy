from typing import TYPE_CHECKING
from pytest import mark
from base64 import b64decode

from liqpy.api.exceptions import LiqPayException

from . import *

if TYPE_CHECKING:
    from liqpy.client import BaseClient


class TestBaseClient:
    @mark.parametrize(
        "is_sandbox,public_key,private_key",
        [
            (True, "sandbox_i0000000", "sandbox_AAAAAA"),
            (False, "i0000000", "AAAAAA"),
        ],
        indirect=["public_key", "private_key"],
    )
    def test_sandbox(self, base_client: "BaseClient", is_sandbox):
        assert base_client.sandbox == is_sandbox

    @mark.parametrize(
        ("action", "params"),
        [
            ("pay", {"amount": 100, "currency": "UAH"}),
            (
                "subscribe",
                {
                    "amount": 500,
                    "currency": "USD",
                    "description": "Test subscription",
                    "order_id": "12345",
                },
            ),
            ("status", {}),
        ],
    )
    def test_request_dict(self, base_client: "BaseClient", action, params, public_key):
        """Test _request_dict method creates proper request dictionary"""
        assert {
            "action": action,
            "version": 3,
            "public_key": public_key,
            **params,
        } == base_client._request_dict(action, **params)

    @mark.parametrize(
        "action,response",
        [
            ("status", {"json": {"status": "success", "payment_id": 123456}}),
            ("status", {"json": {"status": "failure", "payment_id": 123456}}),
            ("status", {"json": {"status": "error", "payment_id": 123456}}),
            ("data", {"json": {"status": "success", "payment_id": 123456}}),
            ("data", {"json": {"status": "faiure", "payment_id": 123456}}),
            ("data", {"json": {"status": "error", "payment_id": 123456}}),
            ("status", {"json": {"status": "success"}}),
            ("unsubscribe", {"json": {"result": "ok", "status": "success"}}),
        ],
        indirect=["response"],
    )
    def test_successful_response(self, base_client: "BaseClient", action, response):
        result = base_client._handle_response(response, action)
        assert isinstance(result, dict)

    @mark.xfail(raises=LiqPayException)
    @mark.parametrize(
        "action,response",
        [
            ("status", {"json": {"result": "ok", "status": "error"}}),
            ("status", {"json": {"result": "error", "status": "hold"}}),
            ("status", {"json": {"status": "error"}}),
            ("status", {"json": {"status": "failure"}}),
        ],
        indirect=["response"],
    )
    def test_error_response(self, base_client: "BaseClient", action, response):
        base_client._handle_response(response, action)

    @mark.parametrize(
        "format,response",
        [
            ("json", {"json": {"data": [{"id": 1}, {"id": 2}]}}),
            (None, {"json": {"data": [{"id": 1}, {"id": 2}]}}),
            ("csv", {"text": "id,amount,currency\n1,100,USD\n2,200,EUR\n"}),
            (
                "xml",
                {"text": "<data><item><id>1</id><amount>100</amount></item></data>"},
            ),
        ],
        indirect=["response"],
    )
    def test_successful_reports_response(
        self, base_client: "BaseClient", response, format
    ):
        result = base_client._handle_reports_response(response, format)
        assert isinstance(result, str)

    @mark.xfail(raises=LiqPayException)
    @mark.parametrize(
        "format,response",
        [
            ("json", {"json": {"result": "error"}}),
            (None, {"json": {"result": "error"}}),
            ("csv", {"json": {"result": "error"}}),
            ("xml", {"json": {"result": "error"}}),
        ],
        indirect=["response"],
    )
    def test_error_reports_response(self, base_client: "BaseClient", response, format):
        base_client._handle_reports_response(response, format)

    @mark.parametrize(
        "response",
        [{"headers": {"Location": "https://example.com/checkout"}}],
        indirect=["response"],
    )
    def test_successful_checkout_response(self, base_client: "BaseClient", response):
        result = base_client._handle_checkout_response(response)
        assert isinstance(result, str) and result != ""

    @mark.xfail(raises=LiqPayException)
    @mark.parametrize(
        "response",
        [{"json": {"result": "error"}}],
        indirect=["response"],
    )
    def test_error_checkout_response(self, base_client: "BaseClient", response):
        base_client._handle_checkout_response(response)

    @mark.parametrize("data", [b"test data for signing", b""])
    def test_sign(self, base_client: "BaseClient", data: bytes):
        """Test sign method produces correct signatures"""
        assert isinstance(signature := base_client.sign(data), bytes)
        assert len(b64decode(signature)) == 20  # SHA1 produces 20 bytes

    def test_sign_consistency(self, base_client: "BaseClient"):
        """Test that sign method produces consistent results"""
        assert len({base_client.sign(b"consistent test data") for _ in range(3)}) == 1

    def test_sign_different_data(self, base_client: "BaseClient"):
        """Test that sign method produces different signatures for different data"""
        assert base_client.sign(b"first data") != base_client.sign(b"second data")
