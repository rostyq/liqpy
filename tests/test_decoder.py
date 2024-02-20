from pytest import fixture
from typing import TYPE_CHECKING
from datetime import datetime
from ipaddress import IPv4Address

from liqpy.api import Decoder
from liqpy.constants import LIQPAY_TZ

from tests import EXAMPLES_DIR

if TYPE_CHECKING:
    from liqpy.types import LiqpayCallbackDict


@fixture
def decoder():
    return Decoder()


def test_decode_status_example(decoder: Decoder):
    with open(EXAMPLES_DIR / "status.json", "r") as fp:
        o: "LiqpayCallbackDict" = decoder.decode(fp.read())

    assert o["create_date"] == datetime(2017, 8, 3, 13, 55, 16, 373000, tzinfo=LIQPAY_TZ)
    assert o["end_date"] == datetime(2017, 8, 3, 13, 55, 29, 972000, tzinfo=LIQPAY_TZ)
    assert o["ip"] == IPv4Address("8.8.8.8")

    assert isinstance(o["version"], int)
    assert isinstance(o["payment_id"], int)
    assert isinstance(o["transaction_id"], int)
    assert isinstance(o["acq_id"], int)
    assert isinstance(o["amount"], float)
    assert isinstance(o["mpi_eci"], int)
