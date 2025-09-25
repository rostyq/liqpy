from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import Parser


def pytest_addoption(parser: "Parser"):
    """Add custom command line options for LiqPay keys."""
    parser.addoption(
        "--private-key",
        action="store",
        default=None,
        help="LiqPay private key for testing",
    )
    parser.addoption(
        "--public-key",
        action="store",
        default=None,
        help="LiqPay public key for testing",
    )
