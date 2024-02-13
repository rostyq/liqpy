from warnings import warn
from contextlib import suppress
from typing import TYPE_CHECKING, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from liqpy.client import Client
from liqpy.dev import LiqPyWarning

if TYPE_CHECKING:
    from liqpy.types import LiqpayCallbackDict


class LiqpayHandler(BaseHTTPRequestHandler):
    """
    Liqpay HTTP request handler for testing

    Do not use in production!
    """

    server: "LiqpayServer"

    @property
    def client(self) -> "Client":
        return self.server.client

    def _is_url_encoded(self) -> bool:
        return self.headers.get("Content-Type", "").startswith(
            "application/x-www-form-urlencoded"
        )

    def _parse_body(self) -> tuple[str, str]:
        if not self._is_url_encoded():
            raise ValueError("Content-Type must be application/x-www-form-urlencoded")

        content_length = int(self.headers.get("Content-Length", -1))

        body = self.rfile.read(content_length).decode()
        result = parse_qs(body)

        signature = result["signature"][0]
        data = result["data"][0]

        return data, signature

    def _handle_webhook(self):
        data, signature = self._parse_body()
        return self.client.callback(data, signature, verify=self.server.verify)

    def do_POST(self):
        self.log_message('"POST %s %s"', self.path, self.protocol_version)
        try:
            self.server.callback(self._handle_webhook())
        finally:
            self.send_response(204)
            self.end_headers()


class LiqpayServer(HTTPServer):
    """
    Liqpay server for testing

    Do not use in production!
    """

    client: "Client"
    verify: bool
    callback: Callable[["LiqpayCallbackDict"], None]

    def __init__(
        self,
        /,
        host: str = "localhost",
        port: int = 8000,
        *,
        callback: Callable[["LiqpayCallbackDict"], None] = lambda _: None,
        client: Optional["Client"] = None,
        timeout: float | None = None,
        verify: bool = True,
    ):
        super().__init__((host, port), LiqpayHandler)
        self.client = Client() if client is None else client
        self.callback = callback
        self.verify = verify

        if timeout is not None:
            self.timeout = float(timeout)

        self.allow_reuse_address = True
        self.allow_reuse_port = True

        warn(
            "LiqPy Test Server is only for development and testing purposes. "
            "Do not use it in production!",
            category=LiqPyWarning,
            stacklevel=2,
        )

    def handle_callback(
        self, timeout: float | None = None
    ) -> Optional["LiqpayCallbackDict"]:
        result: Optional["LiqpayCallbackDict"] = None
        previous_callback = self.callback
        previous_timeout = self.timeout

        if timeout is not None:
            self.timeout = timeout

        def cb(value: "LiqpayCallbackDict"):
            nonlocal result
            result = value

        self.callback = cb
        self.handle_request()

        self.callback = previous_callback
        self.timeout = previous_timeout

        return result


if __name__ == "__main__":
    from logging import getLogger, basicConfig
    from pprint import pprint

    from dotenv import load_dotenv

    basicConfig(level="DEBUG")

    load_dotenv(".env")

    logger = getLogger()

    with LiqpayServer(client=Client(), callback=lambda c: pprint(c)) as server:
        host, port = server.server_address
        logger.info(f"LiqPy Test Server listening on {host}:{port}")

        with suppress(KeyboardInterrupt):
            server.serve_forever()

    logger.info(f"LiqPy Test Server closed")
