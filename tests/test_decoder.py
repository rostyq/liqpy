from typing import TYPE_CHECKING
from decimal import Decimal
from datetime import datetime, UTC
from ipaddress import IPv4Address
from json import dumps

from pytest import mark

from . import *

if TYPE_CHECKING:
    from liqpy.types.response import LiqpayCallbackDict


@mark.parametrize(
    "example",
    [
        {
            "action": "pay",
            "payment_id": 165629,
            "status": "success",
            "version": 3,
            "type": "buy",
            "paytype": "card",
            "public_key": "i000000000",
            "acq_id": 414963,
            "order_id": "98R1U1OV1485849059893399",
            "liqpay_order_id": "NYMK3AE61501685438251925",
            "description": "test",
            "sender_phone": "380950000001",
            "sender_card_mask2": "473118*97",
            "sender_card_bank": "pb",
            "sender_card_type": "visa",
            "sender_card_country": 804,
            "ip": "8.8.8.8",
            "card_token": "2DFBFE626B7341611450DE81E971E948D6F260",
            "info": "My information",
            "amount": 0.02,
            "currency": "UAH",
            "sender_commission": 0.0,
            "receiver_commission": 0.0,
            "agent_commission": 0.0,
            "amount_debit": 0.02,
            "amount_credit": 0.02,
            "commission_debit": 0.0,
            "commission_credit": 0.0,
            "currency_debit": "UAH",
            "currency_credit": "UAH",
            "sender_bonus": 0.0,
            "amount_bonus": 0.0,
            "bonus_type": "bonusplus",
            "bonus_procent": 7.0,
            "authcode_debit": "108527",
            "authcode_credit": "703006",
            "rrn_debit": "000664267598",
            "rrn_credit": "000664267607",
            "mpi_eci": "7",
            "is_3ds": False,
            "create_date": 1501757716373,
            "end_date": 1501757729972,
            "moment_part": True,
            "transaction_id": 165629,
        }
    ],
)
def test_decode_status_example(decoder, example):
    o: "LiqpayCallbackDict" = decoder.decode(dumps(example))

    assert isinstance(o.get("version"), int)
    assert isinstance(o.get("payment_id"), int)
    assert isinstance(o.get("transaction_id"), int)
    assert isinstance(o.get("acq_id"), int)
    assert isinstance(o.get("mpi_eci"), int)

    assert o.get("create_date") == datetime.fromtimestamp(example["create_date"] / 1e3, tz=UTC)
    assert o.get("end_date") == datetime.fromtimestamp(example["end_date"] / 1e3, tz=UTC)
    assert o.get("ip") == IPv4Address(example["ip"])
    assert o.get("amount") == Decimal(str(example["amount"]))
    assert o.get("sender_commission") == Decimal(str(example["sender_commission"]))
    assert o.get("agent_commission") == Decimal(str(example["agent_commission"]))
    assert o.get("amount_debit") == Decimal(str(example["amount_debit"]))
    assert o.get("amount_credit") == Decimal(str(example["amount_credit"]))
    assert o.get("commission_debit") == Decimal(str(example["commission_debit"]))
    assert o.get("commission_credit") == Decimal(str(example["commission_credit"]))
    assert o.get("sender_bonus") == Decimal(str(example["sender_bonus"]))
    assert o.get("amount_bonus") == Decimal(str(example["amount_bonus"]))
