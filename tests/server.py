from typing import TYPE_CHECKING, Optional, List
from pprint import pprint
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

from liqpy.client import Client

if TYPE_CHECKING:
    from liqpy.types import CallbackDict


class LiqpayHandler(BaseHTTPRequestHandler):
    server: "LiqpayServer"

    """Liqpay HTTP request handler for testing."""

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
        return self.client.callback(data, signature, verify=True)

    def _push_callback(self, callback: "CallbackDict"):
        pprint(callback)
        self.server.callback_history.append(callback)

    def do_POST(self):
        self.log_message('"POST %s %s"', self.path, self.protocol_version)
        try:
            self._push_callback(self._handle_webhook())
        # except Exception as e:
        # self.log_error("Error: %s", e)
        finally:
            self.send_response(204)
            self.end_headers()


class LiqpayServer(HTTPServer):
    client: "Client"
    callback_history: List["CallbackDict"]

    """Liqpay server for testing. Do not use in production!"""

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 8000,
        client: Optional["Client"] = None,
    ):
        super().__init__((host, port), LiqpayHandler)
        self.client = Client() if client is None else client
        self.callback_history = []

    @property
    def last_callback(self) -> "CallbackDict":
        return self.callback_history[-1]


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(".env")

    with LiqpayServer(client=Client()) as server:
        host, port = server.server_address
        print(f"LiqPay Test Server listening on {host}:{port}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("LiqPay Test Server stopped.")
        finally:
            server.server_close()
