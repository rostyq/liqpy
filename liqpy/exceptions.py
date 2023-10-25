from typing import Literal, TYPE_CHECKING, Optional
from copy import deepcopy

if TYPE_CHECKING:
    from requests import Response


def is_exception(
    action: str,
    result: Literal["error", "ok"],
    status: Literal["error", "failure", "success"],
) -> bool:
    if result == "error" or status in ["error", "failure"]:
        if action != "status" or status == "error":
            return True
    return False


class LiqPayException(Exception):
    code: str
    details: dict
    response: Optional["Response"] = None

    def __init__(self, code: str, description: str, /, response: Optional["Response"] = None, **kwargs):
        super().__init__(description)
        self.code = code
        self.response = response
        self.details = deepcopy(kwargs)
