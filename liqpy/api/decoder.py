from json import JSONDecoder
from ipaddress import IPv4Address

from liqpy.util.convert import to_datetime


class Decoder(JSONDecoder):
    def __init__(self):
        super().__init__(
            object_hook=self._object_hook,
            parse_float=float,
            parse_int=int,
            parse_constant=None,
            strict=True,
            object_pairs_hook=None,
        )
        self.create_date = to_datetime
        self.end_date = to_datetime
        self.completion_date = to_datetime
        self.mpi_eci = int
        self.ip = IPv4Address
        self.refund_date_last = to_datetime
    
    def _object_hook(self, o: dict, /) -> dict:
        for key, value in o.items():
            try:
                fn = getattr(self, key, None)

                if not callable(fn):
                    continue

                processed = fn(value)

                if processed is not None:
                    o[key] = processed

            except Exception as e:
                raise Exception(f"Failed to post convert {key} parameter.") from e

        return o
    