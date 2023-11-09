from typing import Mapping, Union, Literal, Callable, List, TypedDict
from requests import Response


Proxies = Mapping[str, str]
Timeout = Union[float, tuple[float, float]]
Hook = Callable[[Response], None]
Hooks = Mapping[Literal["response"], Union[Hook, List[Hook]]]
Verify = Union[bool, str]
Cert = Union[str, tuple[str, str]]


class PostParams(TypedDict, total=False):
    stream: bool
    allow_redirects: bool
    proxies: Proxies
    timeout: Timeout
    hooks: Hooks
    verify: Verify
    cert: Cert
