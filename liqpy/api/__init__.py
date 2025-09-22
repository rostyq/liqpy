from base64 import b64encode
from hashlib import sha1, sha3_256
from sys import version_info as v

from httpx import __version__ as _httpx_version
from liqpy import __version__ as _liqpy_version


__all__ = [
    "sign",
    "is_sandbox",
    "BASE_URL",
    "API_VERSION",
    "DATE_FMT",
]

BASE_URL = "https://www.liqpay.ua"
API_VERSION = 3
REQUEST_ENDPOINT = "/api/request"
CHECKOUT_ENDPOINT = "/api/{version}/checkout"
COMMON_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": f"Python/{v.major}.{v.minor}.{v.micro} httpx/{_httpx_version} {__package__}/{_liqpy_version}",
}
DATE_FMT = r"%Y-%m-%d %H:%M:%S"


def is_sandbox(key: str, /) -> bool:
    """Check if the key is a sandbox key"""
    return key.startswith("sandbox_")


def sign(data: bytes, /, key: bytes) -> bytes:
    """
    Sign data string with private key

    Algorithm:

    1. Concatenate the private key with the data string as `key + data + key`
    2. Calculate SHA1 hash of the concatenated string
    3. Encode the hash digest in Base64
    """
    return b64encode(sha1(b''.join((key, data, key))).digest())
