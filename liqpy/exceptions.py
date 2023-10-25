from typing import Literal
from copy import deepcopy


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
    data: dict

    def __init__(self, code: str, description: str, /, **kwargs):
        super().__init__(description)
        self.code = code
        self.data = deepcopy(kwargs)
