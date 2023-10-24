from copy import deepcopy


class LiqPayException(Exception):
    code: str
    data: dict
    
    def __init__(self, code: str, description: str, /, **kwargs):
        super().__init__(description)
        self.code = code
        self.data = deepcopy(kwargs)
