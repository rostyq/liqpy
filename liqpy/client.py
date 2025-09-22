from typing import Optional, Literal, Union, TYPE_CHECKING, Unpack, Any, cast
from warnings import warn
from os import environ
from datetime import datetime, timedelta
from numbers import Number
from re import search
from uuid import UUID

from httpx import (
    Client as _Client,
    AsyncClient as _AsyncClient,
    Response,
    USE_CLIENT_DEFAULT,
)
from httpx._client import UseClientDefault
from httpx._types import TimeoutTypes

from liqpy.dev import LiqpyWarning

from .api import (
    API_VERSION,
    BASE_URL,
    COMMON_HEADERS,
    REQUEST_ENDPOINT,
    CHECKOUT_ENDPOINT,
    is_sandbox,
)
from .api.decoder import LiqpayDecoder
from .api.encoder import LiqpayEncoder
from .api.validation import LiqpayValidator
from .api.exceptions import exception

if TYPE_CHECKING:
    from .types.common import *
    from .types.request import *
    from .types.response import *


__all__ = ["BaseClient", "Client", "AsyncClient"]

TimeoutParam = Union[TimeoutTypes, UseClientDefault]

CHECKOUT_ACTIONS = (
    "auth",
    "pay",
    "hold",
    "subscribe",
    "paydonate",
)


class BaseClient:
    """
    Base class for LiqPay API logic that does not depend on the HTTP client.
    """

    _public_key: str
    __private_key: bytes

    encoder: LiqpayEncoder
    decoder: LiqpayDecoder

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        encoder: Optional[LiqpayEncoder] = None,
        decoder: Optional[LiqpayDecoder] = None,
    ):
        self.update_keys(public_key=public_key, private_key=private_key)
        self.encoder = (
            encoder if encoder is not None else LiqpayEncoder(LiqpayValidator())
        )
        self.decoder = decoder if decoder is not None else LiqpayDecoder()

    @property
    def public_key(self) -> str:
        """Public key used for requests"""
        return self._public_key

    @property
    def sandbox(self) -> bool:
        """Check if client use sandbox LiqPay API"""
        return is_sandbox(self._public_key)

    @property
    def checkout_endpoint(self) -> str:
        """Get the checkout endpoint URL"""
        return CHECKOUT_ENDPOINT.format(version=API_VERSION)

    def update_keys(
        self, /, *, public_key: str | None, private_key: str | None
    ) -> None:
        """Update public and private keys"""
        if public_key is None:
            public_key = environ["LIQPAY_PUBLIC_KEY"]

        if private_key is None:
            private_key = environ["LIQPAY_PRIVATE_KEY"]

        sandbox = is_sandbox(public_key)
        if sandbox != is_sandbox(private_key):
            raise ValueError("Public and private keys must be both sandbox or both not")

        self._public_key = public_key
        self.__private_key = private_key.encode()

        warn(
            "Using %s LiqPay API" % ("sandbox" if sandbox else "live"),
            stacklevel=2,
            category=LiqpyWarning,
        )

    def __repr__(self):
        return f'{self.__class__.__name__}(public_key="{self._public_key}")'

    def payload(
        self, /, action: "LiqpayAction", **kwargs: "Unpack[LiqpayParams]"
    ) -> bytes:
        return self.encoder.payload(
            self.__private_key,
            {
                "action": action,
                "version": API_VERSION,
                "public_key": self._public_key,
                **kwargs,
            },
        )

    def _handle_response(
        self, response: Response, /, action: "LiqpayAction"
    ) -> dict[str, Any]:
        """
        Handle the response from the LiqPay API, detecting errors and returning data.
        """
        if not str(response.headers.get("Content-Type", "")).startswith(
            "application/json"
        ):
            raise exception(response=response)

        data: dict = self.decoder.decode(response.text)

        result: Optional[Literal["ok", "error"]] = data.pop("result", None)
        status = data.get("status")
        err_code = data.pop("err_code", None) or data.pop("code", None)

        if result == "ok" and status != "error":
            return data

        if action in ("status", "data") and data.get("payment_id") is not None:
            return data

        if status in ("error", "failure") or result == "error":
            raise exception(
                code=err_code,
                description=data.pop("err_description", None),
                response=response,
                details=data,
            )

        return data

    def _handle_reports_response(
        self, response: Response, /, format: Optional["Format"]
    ) -> str:
        """
        Handle the response from the reports request, extracting data or raising errors.
        """
        output: str = response.text
        error: dict[str, Any] | None = None

        content_type = str(response.headers.get("Content-Type", ""))

        if content_type.startswith("application/json"):
            if format == "json" or format is None:
                s = search(r'"data":(\[(.*)\])\}$', output)
                if s is not None:
                    output = s.group(1)
                else:
                    error = response.json()
            else:
                error = response.json()

        if error is None:
            return output
        else:
            raise exception(
                code=error.pop("err_code", None) or error.pop("code", None),
                description=error.pop("err_description", ""),
                response=response,
                details=error,
            )

    def _handle_checkout_response(self, response: Response, /) -> str:
        """
        Handle the response for the checkout request, extracting the URL or raising errors.
        """
        if response.next_request is None:
            result = {}
            if str(response.headers.get("Content-Type", "")).startswith(
                "application/json"
            ):
                result = response.json()

            raise exception(
                code=result.pop("err_code", None),
                description=result.pop("err_description", None),
                response=response,
                details=result if len(result) else None,
            )
        else:
            return str(response.next_request.url)

    def callback(self, /, data: str, signature: str, *, verify: bool = True):
        """
        Verify and decode the callback data

        Example:
        >>> client = Client()
        >>> # get data and signature from webhook request body
        >>> order_id = "a1a1a1a1"
        >>> data, signature = client.encode(
        ...     action="pay",
        ...     amount=1,
        ...     order_id=order_id,
        ...     description="Test Encoding",
        ...     currency="USD",
        ... )
        >>> # verify and decode data
        >>> result = client.callback(data, signature)
        >>> assert result["order_id"] == order_id
        >>> assert result["action"] == "pay"
        >>> assert result["amount"] == 1
        >>> assert result["currency"] == "USD"
        >>> assert result["description"] == "Test Encoding"

        [Documentation](https://www.liqpay.ua/en/documentation/api/callback)
        """
        if verify:
            return self.decoder.callback(
                data.encode(), signature.encode(), self.__private_key
            )
        else:
            return self.decoder(data)


class Client(BaseClient):
    """
    Synchronous LiqPay API client using httpx.Client.
    """

    _client: _Client

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        encoder: Optional[LiqpayEncoder] = None,
        decoder: Optional[LiqpayDecoder] = None,
    ):
        super().__init__(
            public_key=public_key,
            private_key=private_key,
            encoder=encoder,
            decoder=decoder,
        )
        self._client = _Client(
            headers=COMMON_HEADERS, base_url=BASE_URL, follow_redirects=False
        )

    def __enter__(self):
        self._client.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        self._client.__exit__(*args, **kwargs)

    def close(self) -> None:
        """Close the client session"""
        self._client.close()

    def request(self, /, action: "LiqpayAction", **kwargs: "Unpack[LiqpayParams]"):
        """Make a request to LiqPay API with the specified action and parameters."""
        content = self.payload(action, **kwargs)
        response = self._client.request("POST", REQUEST_ENDPOINT, content=content)
        return self._handle_response(response.raise_for_status(), action)

    def reports(
        self,
        *,
        timeout: TimeoutParam = USE_CLIENT_DEFAULT,
        **kwargs: "Unpack[ReportsParams]",
    ) -> str:
        """Make a `reports` action request."""
        content = self.payload("reports", **kwargs)
        response = self._client.request(
            "POST", REQUEST_ENDPOINT, content=content, timeout=timeout
        ).raise_for_status()
        return self._handle_reports_response(response, kwargs.get("resp_format"))

    def pay(self, **kwargs: "Unpack[PayParams]"):
        """Make a `pay` action request."""
        return cast("PayResult", self.request("pay", **kwargs))

    def hold(self, **kwargs: "Unpack[LiqpayParams]"):
        """Make a `hold` action request."""
        return self.request("hold", **kwargs)

    def unsubscribe(self, order_id: str | UUID):
        """Make an `unsubscribe` action request."""
        return self.request("unsubscribe", order_id=order_id)

    def refund(self, **kwargs: "Unpack[AmountIdParams]"):
        """Make a `refund` action request."""
        return cast("LiqpayRefundDict", self.request("refund", **kwargs))

    def complete(self, **kwargs: "Unpack[AmountIdParams]"):
        """Make a `hold_completion` action request."""
        return self.request("hold_completion", **kwargs)

    def checkout(self, **kwargs: Unpack["CheckoutParams"]) -> str:
        """Make a Client-Server checkout request. Returns a URL to redirect the user to."""
        content = self.payload(**kwargs)
        response = self._client.request("POST", self.checkout_endpoint, content=content)
        return self._handle_checkout_response(response)

    def payments(self, **kwargs: "Unpack[PaymentsParams]"):
        """Make a `reports` action request and parse the result as JSON."""
        result = self.reports(resp_format="json", **kwargs)
        return cast(list[dict[str, Any]], self.decoder.decode(result))

    def subscribe(self, **kwargs: Unpack["SubscribeParams"]):
        """Make a `subscribe` action request."""
        return self.request("subscribe", **kwargs)

    def subscription(self, **kwargs: Unpack["PaymentDict"]):
        """Edit an existing subscription."""
        return self.request("subscribe_update", **kwargs)

    def data(self, **kwargs: "Unpack[DataParams]"):
        """Adding an info to already created payment."""
        return self.request("data", **kwargs)

    def ticket(self, **kwargs: Unpack["TicketParams"]) -> None:
        """Send a receipt to the customer."""
        self.request("ticket", **kwargs)

    def status(self, **kwargs: "Unpack[IdParams]"):
        """Get the status of a payment."""
        return self.request("status", **kwargs)


class AsyncClient(BaseClient):
    """
    Asynchronous LiqPay API client using httpx.AsyncClient.
    """

    _client: _AsyncClient

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        encoder: Optional[LiqpayEncoder] = None,
        decoder: Optional[LiqpayDecoder] = None,
    ):
        super().__init__(
            public_key=public_key,
            private_key=private_key,
            encoder=encoder,
            decoder=decoder,
        )
        self._client = _AsyncClient(
            headers=COMMON_HEADERS, base_url=BASE_URL, follow_redirects=False
        )

    async def __aenter__(self):
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._client.__aexit__(*args, **kwargs)

    async def close(self) -> None:
        """Close the client session"""
        await self._client.aclose()

    async def request(self, /, action: "LiqpayAction", **kwargs: "Unpack[LiqpayParams]"):
        """Make a request to LiqPay API with the specified action and parameters."""
        content = self.payload(action, **kwargs)
        response = await self._client.request("POST", REQUEST_ENDPOINT, content=content)
        return self._handle_response(response.raise_for_status(), action)

    async def reports(
        self,
        *,
        timeout: TimeoutParam = USE_CLIENT_DEFAULT,
        **kwargs: "Unpack[ReportsParams]",
    ) -> str:
        """Make a `reports` action request."""
        content = self.payload("reports", **kwargs)
        response = await self._client.request(
            "POST", REQUEST_ENDPOINT, content=content, timeout=timeout
        )
        return self._handle_reports_response(response.raise_for_status(), kwargs.get("resp_format"))

    async def pay(self, **kwargs: "Unpack[PayParams]"):
        """Make a `pay` action request."""
        return cast("PayResult", await self.request("pay", **kwargs))

    async def hold(self, **kwargs: "Unpack[LiqpayParams]"):
        """Make a `hold` action request."""
        return await self.request("hold", **kwargs)

    async def unsubscribe(self, order_id: str | UUID):
        """Make an `unsubscribe` action request."""
        return await self.request("unsubscribe", order_id=order_id)

    async def refund(self, **kwargs: "Unpack[AmountIdParams]"):
        """Make a `refund` action request."""
        return cast("LiqpayRefundDict", await self.request("refund", **kwargs))

    async def complete(self, **kwargs: "Unpack[AmountIdParams]"):
        """Make a `hold_completion` action request."""
        return await self.request("hold_completion", **kwargs)

    async def checkout(self, **kwargs: Unpack["CheckoutParams"]) -> str:
        """Make a Client-Server checkout request. Returns a URL to redirect the user to."""
        content = self.payload(**kwargs)
        response = await self._client.request("POST", self.checkout_endpoint, content=content)
        return self._handle_checkout_response(response)

    async def payments(self, **kwargs: "Unpack[PaymentsParams]"):
        """Make a `reports` action request and parse the result as JSON."""
        result = await self.reports(resp_format="json", **kwargs)
        return cast(list[dict[str, Any]], self.decoder.decode(result))

    async def subscribe(self, **kwargs: Unpack["SubscribeParams"]):
        """Make a `subscribe` action request."""
        return await self.request("subscribe", **kwargs)

    async def subscription(self, **kwargs: Unpack["PaymentDict"]):
        """Edit an existing subscription."""
        return await self.request("subscribe_update", **kwargs)

    async def data(self, **kwargs: "Unpack[DataParams]"):
        """Adding an info to already created payment."""
        return await self.request("data", **kwargs)

    async def ticket(self, **kwargs: Unpack["TicketParams"]) -> None:
        """Send a receipt to the customer."""
        await self.request("ticket", **kwargs)

    async def status(self, **kwargs: "Unpack[IdParams]"):
        """Get the status of a payment."""
        return await self.request("status", **kwargs)
