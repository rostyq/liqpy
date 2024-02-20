from typing import TypedDict, TYPE_CHECKING
from json import load

from liqpy.api import encode, sign, decode

from tests import EXAMPLES_DIR

if TYPE_CHECKING:
    from liqpy.types import LiqpayRequestDict


class Example(TypedDict):
    json: "LiqpayRequestDict"
    key: str
    data: str
    signature: str


def test_signature_example():
    """
    Test signature example from the documentation

    https://www.liqpay.ua/en/documentation/data_signature
    """
    with open(EXAMPLES_DIR / "sign.json") as f:
        example: Example = load(f)
    
    data = encode(example["json"])
    assert data == example["data"].encode()

    signature = sign(data, example["key"].encode())
    assert signature == example["signature"].encode()
    