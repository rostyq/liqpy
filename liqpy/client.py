from warnings import warn
from typing import Optional, Literal, Union, TYPE_CHECKING, Unpack, AnyStr, TypedDict
from os import environ
from logging import getLogger
from datetime import datetime, timedelta
from numbers import Number
from re import search
from uuid import UUID

from httpx import Client as _Client, AsyncClient as _AsyncClient, Response
from secret_type import secret, Secret

from liqpy.dev import LiqpyWarning

from .api import (
    VERSION,
    BASE_URL,
    COMMON_HEADERS,
    REQUEST_ENDPOINT,
    CHECKOUT_ENDPOINT,
    sign,
    request,
    encode,
    decode,
    payload,
    is_sandbox,
    exception,
    BasePreprocessor,
    BaseValidator,
    JSONEncoder,
    JSONDecoder,
    Decoder,
    Encoder,
    Preprocessor,
    Validator,
)

if TYPE_CHECKING:
    from .types.common import Language, Currency, SubscribePeriodicity, PayOption
    from .types.request import Format, LiqpayRequestDict, Action
    from .types.callback import LiqpayCallbackDict, LiqpayRefundDict


__all__ = ["BaseClient", "Client", "AsyncClient"]


logger = getLogger(__package__)


CHECKOUT_ACTIONS = (
    "auth",
    "pay",
    "hold",
    "subscribe",
    "paydonate",
)


class InitParams(TypedDict, total=False):
    validator: BaseValidator
    preprocessor: BasePreprocessor
    encoder: JSONEncoder
    decoder: JSONDecoder


class BaseClient:
    """
    Base class for LiqPay API logic that does not depend on the HTTP client.
    """

    _public_key: str
    _private_key: Secret[bytes]

    validator: BaseValidator
    preprocessor: BasePreprocessor
    encoder: JSONEncoder
    decoder: JSONDecoder

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        validator: Optional[BaseValidator] = None,
        preprocessor: Optional[BasePreprocessor] = None,
        encoder: Optional[JSONEncoder] = None,
        decoder: Optional[JSONDecoder] = None,
    ):
        self.update_keys(public_key=public_key, private_key=private_key)
        self.validator = validator if validator is not None else Validator()
        self.preprocessor = preprocessor if preprocessor is not None else Preprocessor()
        self.encoder = encoder if encoder is not None else Encoder()
        self.decoder = decoder if decoder is not None else Decoder()

    @property
    def public_key(self) -> str:
        """Public key used for requests"""
        return self._public_key

    @property
    def sandbox(self) -> bool:
        """Check if client use sandbox LiqPay API"""
        return is_sandbox(self._public_key)

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
        self._private_key = secret(private_key.encode())

        warn(
            "Using %s LiqPay API" % ("sandbox" if sandbox else "live"),
            stacklevel=2,
            category=LiqpyWarning,
        )

    def __repr__(self):
        return f'{self.__class__.__name__}(public_key="{self._public_key}")'

    def _callback(
        self, /, data: bytes, signature: bytes, *, verify: bool = True
    ) -> "LiqpayCallbackDict":
        if verify:
            self.verify(data, signature)
        else:
            warn(
                "Skipping LiqPay signature verification",
                stacklevel=2,
                category=LiqpyWarning,
            )

        return decode(data, decoder=self.decoder)

    def sign(self, data: bytes, /) -> bytes:
        """
        Sign data string with private key

        See `liqpy.api.sign` for more information.
        """
        with self._private_key.dangerous_reveal() as pk:
            return sign(data, key=pk)

    def encode(
        self, /, action: str, **kwargs: Unpack["LiqpayRequestDict"]
    ) -> tuple[bytes, bytes]:
        """
        Encode parameters into data and signature strings

        >>> data, signature = client.encode("status", order_id="a1a1a1a1")

        See `liqpy.api.encode` for more information.
        """
        data = encode(
            request(action, public_key=self._public_key, version=VERSION, **kwargs),
            filter_none=True,
            validator=self.validator,
            preprocessor=self.preprocessor,
            encoder=self.encoder,
        )
        signature = self.sign(data)
        return data, signature

    def payload(self, /, action: str, **kwargs: Unpack["LiqpayRequestDict"]) -> bytes:
        data, signature = self.encode(action, **kwargs)
        return payload(data=data, signature=signature)

    def is_valid(self, /, data: bytes, signature: bytes) -> bool:
        """
        Check if the signature is valid

        Used for verification in `liqpy.Client.verify`.
        """
        return self.sign(data) == signature

    def verify(self, /, data: bytes, signature: bytes) -> None:
        """
        Verify data signature

        Raises an `AssertionError` if `data` does not match the `signature`.

        Used for verification in `liqpy.Client.callback`.
        """
        assert self.is_valid(data, signature), "Invalid signature"

    def _handle_response(self, response: Response, action: str) -> dict:
        """
        Handle the response from the LiqPay API, detecting errors and returning data.
        """
        if not response.headers.get("Content-Type", "").startswith("application/json"):
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
        self, response: Response, format: Optional["Format"]
    ) -> str:
        """
        Handle the response from the reports request, extracting data or raising errors.
        """
        output: str = response.text
        error: dict | None = None

        content_type = response.headers.get("Content-Type", "")

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

    def callback(self, /, data: AnyStr, signature: AnyStr, *, verify: bool = True):
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
        if isinstance(data, str):
            data = data.encode()

        if isinstance(signature, str):
            signature = signature.encode()

        result = self._callback(data, signature, verify=verify)
        version = result.get("version")

        if version != VERSION:
            logger.warning("Callback version mismatch: %s != %s", version, VERSION)

        return result

    def _handle_checkout_response(self, response: Response) -> str:
        """
        Handle the response for the checkout request, extracting the URL or raising errors.
        """
        if response.next_request is None:
            result = {}
            if response.headers.get("Content-Type", "").startswith("application/json"):
                result = response.json()

            raise exception(
                code=result.pop("err_code", None),
                description=result.pop("err_description", None),
                response=response,
                details=result if len(result) else None,
            )
        else:
            return str(response.next_request.url)


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
        **kwargs: Unpack[InitParams],
    ):
        super().__init__(public_key=public_key, private_key=private_key, **kwargs)
        self._client = _Client(
            headers=COMMON_HEADERS, base_url=BASE_URL, follow_redirects=False
        )

    def __enter__(self) -> "_Client":
        self._client.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        self._client.__exit__(*args, **kwargs)

    def close(self) -> None:
        """Close the client session"""
        self._client.close()

    def request(self, /, action: "Action", **kwargs: "LiqpayRequestDict") -> dict:
        content = self.payload(action, **kwargs)
        response = self._client.request("POST", REQUEST_ENDPOINT, content=content)
        return self._handle_response(response.raise_for_status(), action)

    def reports(
        self,
        /,
        date_from: Union[datetime, str, int, timedelta],
        date_to: Union[datetime, str, int, timedelta],
        *,
        format: Optional["Format"] = None,
    ) -> str:
        content = self.payload(
            "reports",
            date_from=date_from,
            date_to=date_to,
            resp_format=format,
        )
        response = self._client.request("POST", REQUEST_ENDPOINT, content=content)
        return self._handle_reports_response(response.raise_for_status(), format)

    def pay(
        self,
        /,
        amount: Number,
        order_id: str | UUID,
        card: str,
        card_cvv: str,
        card_exp_month: str,
        card_exp_year: str,
        currency: "Currency",
        description: str,
        **kwargs: "LiqpayRequestDict",
    ) -> "LiqpayCallbackDict":
        """
        Request a `pay` action from LiqPay API

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/pay/doc)
        """
        return self.request(
            "pay",
            order_id=order_id,
            amount=amount,
            card=card,
            card_cvv=card_cvv,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            currency=currency,
            description=description,
            **kwargs,
        )

    def hold(
        self,
        /,
        amount: Number,
        order_id: str | UUID,
        card: str,
        card_cvv: str,
        card_exp_month: str,
        card_exp_year: str,
        currency: "Currency",
        description: str,
        **kwargs: "LiqpayRequestDict",
    ) -> "LiqpayCallbackDict":
        """
        Request a `hold` action from LiqPay API

        Use `liqpy.client.Client.complete` to complete the hold.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/hold/doc)
        """
        return self.request(
            "hold",
            order_id=order_id,
            amount=amount,
            card=card,
            card_cvv=card_cvv,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            currency=currency,
            description=description,
            **kwargs,
        )

    def unsubscribe(self, /, opid: int | str | UUID) -> "LiqpayCallbackDict":
        """
        Cancel recurring payments for the order

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/unsubscribe/doc)
        """
        return self.request("unsubscribe", opid=opid)

    def refund(
        self,
        /,
        opid: int | str | UUID,
        *,
        amount: Number | None = None,
    ) -> "LiqpayRefundDict":
        """
        Make a refund request to LiqPay API

        Use `payment_id` (`int` type) to refund from recurring payments.
        """
        return self.request("refund", opid=opid, amount=amount)

    def complete(
        self, /, opid: int | str | UUID, *, amount: Number | None = None
    ) -> "LiqpayCallbackDict":
        """
        Request a `hold_completion` action from LiqPay API

        Use `liqpy.client.Client.hold` to request a hold action.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/hold_completion/doc)
        """
        return self.request("hold_completion", opid=opid, amount=amount)

    def checkout(
        self,
        /,
        action: Literal["auth", "pay", "hold", "subscribe", "paydonate"],
        *,
        order_id: str | UUID,
        amount: Number,
        currency: "Currency",
        description: str,
        expired_date: str | datetime | timedelta | None = None,
        paytypes: Optional[list["PayOption"]] = None,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> str:
        """
        Make a Client-Server checkout request to LiqPay API

        Returns a url to redirect the user to.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/checkout/doc)
        """
        assert (
            action in CHECKOUT_ACTIONS
        ), "Invalid action. Must be one of: %s" % ",".join(CHECKOUT_ACTIONS)

        content = self.payload(
            action,
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description,
            expired_date=expired_date,
            paytypes=paytypes,
            **kwargs,
        )
        response = self._client.request("POST", CHECKOUT_ENDPOINT, content=content)
        return self._handle_checkout_response(response)

    def payments(
        self,
        /,
        date_from: Union[datetime, str, int, timedelta],
        date_to: Union[datetime, str, int, timedelta],
    ) -> list["LiqpayCallbackDict"]:
        """
        Get an archive of received payments

        For a significant amount of data use `liqpy.client.Client.reports` with `csv` format instead.
        """
        return self.decoder.decode(self.reports(date_from, date_to, format="json"))

    def subscribe(
        self,
        /,
        order_id: str | UUID,
        amount: Number,
        card: str,
        card_cvv: str,
        card_exp_month: str,
        card_exp_year: str,
        currency: "Currency",
        description: str,
        subscribe_periodicity: "SubscribePeriodicity",
        subscribe_date_start: datetime | str | timedelta | None | Number,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> "LiqpayCallbackDict":
        """
        Create an order with recurring payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/subscribe/doc)
        """
        return self.request(
            "subscribe",
            order_id=order_id,
            amount=amount,
            card=card,
            card_cvv=card_cvv,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            currency=currency,
            description=description,
            subscribe_date_start=subscribe_date_start,
            subscribe_periodicity=subscribe_periodicity,
            **kwargs,
        )

    def subscription(
        self,
        /,
        order_id: str | UUID,
        *,
        amount: Number,
        currency: "Currency",
        description: str,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> "LiqpayCallbackDict":
        """
        Edit an existing recurring payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/subscribe_update/doc)
        """
        return self.request(
            "subscribe_update",
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description,
            **kwargs,
        )

    def data(self, /, opid: str | int | UUID, *, info: str) -> "LiqpayCallbackDict":
        """
        Adding an info to already created payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/data/doc)
        """
        return self.request("data", opid=opid, info=info)

    def ticket(
        self,
        /,
        order_id: str | UUID,
        email: str,
        *,
        payment_id: Optional[int] = None,
        language: Optional["Language"] = None,
    ) -> None:
        """
        Send a receipt to the customer

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/ticket/doc)
        """
        self.request(
            "ticket",
            order_id=order_id,
            email=email,
            payment_id=payment_id,
            language=language,
        )

    def status(self, opid: int | str | UUID, /) -> "LiqpayCallbackDict":
        """
        Get the status of a payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/status/doc)
        """
        return self.request("status", opid=opid)


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
        **kwargs: Unpack[InitParams],
    ):
        super().__init__(public_key=public_key, private_key=private_key, **kwargs)
        self._client = _AsyncClient(
            headers=COMMON_HEADERS, base_url=BASE_URL, follow_redirects=False
        )

    async def __aenter__(self) -> "_AsyncClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._client.__aexit__(*args, **kwargs)

    async def close(self) -> None:
        """Close the client session"""
        await self._client.aclose()

    async def request(self, /, action: "Action", **kwargs: "LiqpayRequestDict") -> dict:
        content = self.payload(action, **kwargs)
        response = await self._client.request("POST", REQUEST_ENDPOINT, content=content)
        return self._handle_response(response.raise_for_status(), action)

    async def reports(
        self,
        /,
        date_from: Union[datetime, str, int, timedelta],
        date_to: Union[datetime, str, int, timedelta],
        *,
        format: Optional["Format"] = None,
    ) -> str:
        content = self.payload(
            "reports",
            date_from=date_from,
            date_to=date_to,
            resp_format=format,
        )
        response = await self._client.request("POST", REQUEST_ENDPOINT, content=content)
        return self._handle_reports_response(response.raise_for_status(), format)

    async def pay(
        self,
        /,
        amount: Number,
        order_id: str | UUID,
        card: str,
        card_cvv: str,
        card_exp_month: str,
        card_exp_year: str,
        currency: "Currency",
        description: str,
        **kwargs: "LiqpayRequestDict",
    ) -> "LiqpayCallbackDict":
        """
        Request a `pay` action from LiqPay API

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/pay/doc)
        """
        return await self.request(
            "pay",
            order_id=order_id,
            amount=amount,
            card=card,
            card_cvv=card_cvv,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            currency=currency,
            description=description,
            **kwargs,
        )

    async def hold(
        self,
        /,
        amount: Number,
        order_id: str | UUID,
        card: str,
        card_cvv: str,
        card_exp_month: str,
        card_exp_year: str,
        currency: "Currency",
        description: str,
        **kwargs: "LiqpayRequestDict",
    ) -> "LiqpayCallbackDict":
        """
        Request a `hold` action from LiqPay API

        Use `liqpy.client.Client.complete` to complete the hold.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/hold/doc)
        """
        return await self.request(
            "hold",
            order_id=order_id,
            amount=amount,
            card=card,
            card_cvv=card_cvv,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            currency=currency,
            description=description,
            **kwargs,
        )

    async def unsubscribe(self, /, opid: int | str | UUID) -> "LiqpayCallbackDict":
        """
        Cancel recurring payments for the order

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/unsubscribe/doc)
        """
        return await self.request("unsubscribe", opid=opid)

    async def refund(
        self,
        /,
        opid: int | str | UUID,
        *,
        amount: Number | None = None,
    ) -> "LiqpayRefundDict":
        """
        Make a refund request to LiqPay API

        Use `payment_id` (`int` type) to refund from recurring payments.
        """
        return await self.request("refund", opid=opid, amount=amount)

    async def complete(
        self, /, opid: int | str | UUID, *, amount: Number | None = None
    ) -> "LiqpayCallbackDict":
        """
        Request a `hold_completion` action from LiqPay API

        Use `liqpy.client.Client.hold` to request a hold action.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/hold_completion/doc)
        """
        return await self.request("hold_completion", opid=opid, amount=amount)

    async def checkout(
        self,
        /,
        action: Literal["auth", "pay", "hold", "subscribe", "paydonate"],
        *,
        order_id: str | UUID,
        amount: Number,
        currency: "Currency",
        description: str,
        expired_date: str | datetime | timedelta | None = None,
        paytypes: Optional[list["PayOption"]] = None,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> str:
        """
        Make a Client-Server checkout request to LiqPay API

        Returns a url to redirect the user to.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/checkout/doc)
        """
        assert (
            action in CHECKOUT_ACTIONS
        ), "Invalid action. Must be one of: %s" % ",".join(CHECKOUT_ACTIONS)
        content = self.payload(
            action,
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description,
            expired_date=expired_date,
            paytypes=paytypes,
            **kwargs,
        )

        response = await self._client.request(
            "POST", CHECKOUT_ENDPOINT, content=content
        )
        return self._handle_checkout_response(response)

    async def payments(
        self,
        /,
        date_from: Union[datetime, str, int, timedelta],
        date_to: Union[datetime, str, int, timedelta],
    ) -> list["LiqpayCallbackDict"]:
        """
        Get an archive of received payments

        For a significant amount of data use `liqpy.client.Client.reports` with `csv` format instead.
        """
        result = await self.reports(date_from, date_to, format="json")
        return self.decoder.decode(result)

    async def subscribe(
        self,
        /,
        order_id: str | UUID,
        amount: Number,
        card: str,
        card_cvv: str,
        card_exp_month: str,
        card_exp_year: str,
        currency: "Currency",
        description: str,
        subscribe_periodicity: "SubscribePeriodicity",
        subscribe_date_start: datetime | str | timedelta | None | Number,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> "LiqpayCallbackDict":
        """
        Create an order with recurring payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/subscribe/doc)
        """
        return await self.request(
            "subscribe",
            order_id=order_id,
            amount=amount,
            card=card,
            card_cvv=card_cvv,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year,
            currency=currency,
            description=description,
            subscribe_date_start=subscribe_date_start,
            subscribe_periodicity=subscribe_periodicity,
            **kwargs,
        )

    async def subscription(
        self,
        /,
        order_id: str | UUID,
        *,
        amount: Number,
        currency: "Currency",
        description: str,
        **kwargs: Unpack["LiqpayRequestDict"],
    ) -> "LiqpayCallbackDict":
        """
        Edit an existing recurring payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/subscribe_update/doc)
        """
        return await self.request(
            "subscribe_update",
            order_id=order_id,
            amount=amount,
            currency=currency,
            description=description,
            **kwargs,
        )

    async def data(
        self, /, opid: str | int | UUID, *, info: str
    ) -> "LiqpayCallbackDict":
        """
        Adding an info to already created payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/data/doc)
        """
        return await self.request("data", opid=opid, info=info)

    async def ticket(
        self,
        /,
        order_id: str | UUID,
        email: str,
        *,
        payment_id: Optional[int] = None,
        language: Optional["Language"] = None,
    ) -> None:
        """
        Send a receipt to the customer

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/ticket/doc)
        """
        await self.request(
            "ticket",
            order_id=order_id,
            email=email,
            payment_id=payment_id,
            language=language,
        )

    async def status(self, opid: int | str | UUID, /) -> "LiqpayCallbackDict":
        """
        Get the status of a payment

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/status/doc)
        """
        return await self.request("status", opid=opid)
