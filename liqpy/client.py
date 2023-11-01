from typing import Optional, Literal, Union, TYPE_CHECKING, Iterable
from hashlib import sha1
from base64 import b64encode, b64decode
from os import environ
from json import dumps, loads
from logging import getLogger
from datetime import datetime
from numbers import Number
from re import search

from requests import Session, Response
from secret_type import secret, Secret

from .constants import VERSION, REQUEST_URL, CHECKOUT_URL
from .exceptions import exception_factory, is_exception, LiqPayException
from .util import (
    to_milliseconds,
    to_dict,
    is_sandbox,
    format_date,
    filter_none,
    verify_url,
)

if TYPE_CHECKING:
    from .types import (
        CallbackDict,
        Language,
        Format,
        Currency,
        PayType,
        RROInfoDict,
        SplitRuleDict,
        SubscribePeriodicity,
        DetailAddendaDict,
    )


__all__ = ["Client"]


logger = getLogger(__name__)


class Client:
    """
    [LiqPay API](https://www.liqpay.ua/en/documentation/api/home) authorized client.

    Intialize by setting environment variables
    `LIQPAY_PUBLIC_KEY` and `LIQPAY_PRIVATE_KEY`:
    >>> from liqpy.client import Client
    >>> client = Client()

    Or pass them as arguments:
    >>> client = Client(public_key="...", private_key="...")

    For using custom session object pass it as an keyword argument:
    >>> from requests import Session
    >>> with Session() as session:
    >>>     client = Client(session=session)

    Client implements context manager interface same as `requests.Session`:
    >>> with Client() as client:
    >>>     pass
    >>> # client.session is closed
    """

    session: Session

    _public_key: str
    _private_key: Secret[str]

    def __init__(
        self,
        /,
        public_key: str | None = None,
        private_key: str | None = None,
        *,
        session: Session = None,
    ):
        self.update_keys(public_key, private_key)
        self.session = Session() if session is None else session

    @property
    def public_key(self) -> str:
        """Public key used for requests."""
        return self._public_key

    @property
    def sandbox(self) -> bool:
        """Check if client use sandbox LiqPay API."""
        return is_sandbox(self._public_key)

    def update_keys(self, /, public_key: str | None, private_key: str | None) -> None:
        """Update public and private keys."""
        if public_key is None:
            public_key = environ["LIQPAY_PUBLIC_KEY"]
        else:
            public_key = str(public_key)

        if private_key is None:
            private_key = environ["LIQPAY_PRIVATE_KEY"]
        else:
            private_key = str(private_key)

        sandbox = is_sandbox(public_key)
        if sandbox != is_sandbox(private_key):
            raise ValueError("Public and private keys must be both sandbox or both not")

        self._public_key = public_key
        self._private_key = secret(private_key)

        if sandbox:
            logger.warning("Using sandbox LiqPay API.")

    def __repr__(self):
        return f'{self.__class__.__name__}(public_key="{self._public_key}")'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    def __del__(self):
        self.session.close()

    def _prepare(self, /, action: str, **kwargs) -> dict:
        return {
            **filter_none(kwargs),
            "public_key": self._public_key,
            "version": VERSION,
            "action": str(action),
        }

    def _post(self, url: str, /, data: str, signature: str, **kwargs) -> "Response":
        response = self.session.post(url, data=to_dict(data, signature), **kwargs)
        response.raise_for_status()
        return response

    def _post_request(
        self,
        /,
        data: str,
        signature: str,
        *,
        stream: bool = False,
        **kwargs,
    ) -> "Response":
        return self._post(REQUEST_URL, data, signature, stream=stream, **kwargs)

    def _post_checkout(
        self,
        /,
        data: str,
        signature: str,
        *,
        redirect: bool = False,
        **kwargs,
    ) -> "Response":
        return self._post(
            CHECKOUT_URL, data, signature, allow_redirects=redirect, **kwargs
        )

    def _callback(
        self, data: str, signature: str, *, verify: bool = True
    ) -> "CallbackDict":
        if verify:
            self.verify(data, signature)
        else:
            logger.warning("Skipping signature verification")

        return loads(b64decode(data))

    def sign(self, data: str, /) -> str:
        """Sign data string with private key."""
        with self._private_key.dangerous_reveal() as pk:
            payload = f"{pk}{data}{pk}".encode()
            return b64encode(sha1(payload).digest()).decode()

    def encode(self, /, action: str, **kwargs) -> tuple[str, str]:
        """
        Encode parameters into data and signature strings.
        See usage example in `liqpy.Client.callback`.
        """
        data = dumps(self._prepare(action, **kwargs))
        data = b64encode(data.encode()).decode()
        signature = self.sign(data)

        return data, signature

    def is_valid(self, /, data: str, signature: str) -> bool:
        """
        Check if the signature is valid.
        Used for verification in `liqpy.Client.verify`.
        """
        return self.sign(data) == signature

    def verify(self, /, data: str, signature: str) -> None:
        """
        Verify if the signature is valid. Raise an `AssertionError` if not.
        Used for verification in `liqpy.Client.callback`.
        """
        assert self.is_valid(data, signature), "Invalid signature"

    def request(self, action: str, **kwargs) -> dict:
        """
        Make a Server-Server request to LiqPay API.
        """
        response = self._post_request(*self.encode(action, **kwargs))

        if not response.headers.get("Content-Type", "").startswith("application/json"):
            raise LiqPayException(response=response)

        result: dict = response.json()

        if is_exception(action, result.pop("result", ""), result.get("status")):
            raise exception_factory(
                code=result.pop("err_code", None),
                description=result.pop("err_description", None),
                response=response,
                details=result,
            )

        return result

    def checkout(
        self,
        /,
        action: Literal["auth", "pay", "hold", "subscribe", "paydonate"],
        order_id: str,
        *,
        amount: Number,
        currency: "Currency",
        description: str,
        rro_info: Optional["RROInfoDict"] = None,
        expired_date: Optional[Union[datetime, str, Number]] = None,
        language: Optional["Language"] = None,
        paytypes: Optional[Iterable["PayType"]] = None,
        result_url: Optional[str] = None,
        server_url: Optional[str] = None,
        verifycode: bool = False,
        split_rules: Optional[Iterable["SplitRuleDict"]] = None,
        sender_address: Optional[str] = None,
        sender_city: Optional[str] = None,
        sender_country_code: Optional[str] = None,
        sender_first_name: Optional[str] = None,
        sender_last_name: Optional[str] = None,
        sender_postal_code: Optional[str] = None,
        letter_of_credit: Optional[str] = None,
        letter_of_credit_date: Optional[Union[datetime, str, Number]] = None,
        subscribe_date_start: Optional[Union[datetime, str, Number]] = None,
        subscribe_periodicity: Optional["SubscribePeriodicity"] = None,
        customer: Optional[str] = None,
        recurring_by_token: bool = False,
        customer_user_id: Optional[str] = None,
        detail_addenda: Optional["DetailAddendaDict"] = None,
        info: Optional[str] = None,
        product_category: Optional[str] = None,
        product_description: Optional[str] = None,
        product_name: Optional[str] = None,
        product_url: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Make a Client-Server checkout request to LiqPay API.

        `kwargs` are passed to `requests.Session.post` method.

        [Documentation](https://www.liqpay.ua/en/documentation/api/aquiring/checkout/doc)
        """
        assert action in (
            "auth",
            "pay",
            "hold",
            "subscribe",
            "paydonate",
        ), "Invalid action. Must be one of: auth, pay, hold, subscribe, paydonate"

        assert isinstance(amount, Number), "Amount must be a number"

        assert currency in (
            "EUR",
            "UAH",
            "USD",
        ), "Invalid currency. Must be one of: EUR, UAH, USD"

        order_id = str(order_id)
        assert len(order_id) <= 255, "Order id must be less than 255 characters"

        params = {
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "description": str(description),
            "rro_info": rro_info,
            "sender_address": sender_address,
            "sender_city": sender_city,
            "sender_country_code": sender_country_code,
            "sender_first_name": sender_first_name,
            "sender_last_name": sender_last_name,
            "sender_postal_code": sender_postal_code,
            "letter_of_credit": letter_of_credit,
            "customer_user_id": customer_user_id,
            "info": info,
        }

        if action == "auth" and verifycode:
            params["verifycode"] = "Y"

        if language is not None:
            assert language in ("en", "uk"), "Invalid language. Must be one of: en, uk"
            params["language"] = language

        if result_url is not None:
            verify_url(result_url)
            params["result_url"] = result_url

        if server_url is not None:
            verify_url(server_url)
            params["server_url"] = server_url

        if paytypes is not None:
            paytypes = set(paytypes)
            assert paytypes.issubset(
                (
                    "card",
                    "liqpay",
                    "privat24",
                    "masterpass",
                    "moment_part",
                    "cash",
                    "invoice",
                    "qr",
                )
            ), "Invalid paytypes. Must be one of: card, liqpay, privat24, masterpass, moment_part, cash, invoice, qr"
            params["paytypes"] = ",".join(paytypes)

        if action == "subscribe":
            if subscribe_date_start is None:
                subscribe_date_start = datetime.utcnow()

            if subscribe_periodicity is not None:
                assert subscribe_periodicity in (
                    "month",
                    "year",
                ), "Invalid subscribe periodicity. Must be one of: month, year"

            params.update(
                subscribe=1,
                subscribe_date_start=format_date(subscribe_date_start),
                subscribe_periodicity=subscribe_periodicity or "month",
            )

        if customer is not None:
            assert len(customer) <= 100, "Customer must be less than 100 characters"
            params["customer"] = customer

        if expired_date is not None:
            params["expired_date"] = format_date(expired_date)

        if split_rules is not None and len(split_rules) > 0:
            params["split_rules"] = dumps(list(split_rules))

        if letter_of_credit_date is not None:
            params["letter_of_credit_date"] = format_date(letter_of_credit_date)

        if recurring_by_token:
            assert (
                server_url is not None
            ), "Server url must be specified for recurring by token"
            params["recurringbytoken"] = "1"

        if detail_addenda is not None:
            params["dae"] = b64encode(dumps(detail_addenda).encode()).decode()

        if product_category is not None:
            assert (
                len(product_category) <= 25
            ), "Product category must be less than 25 characters"
            params["product_category"] = product_category

        if product_description is not None:
            assert (
                len(product_description) <= 500
            ), "Product description must be less than 500 characters"
            params["product_description"] = product_description

        if product_name is not None:
            assert (
                len(product_name) <= 100
            ), "Product name must be less than 100 characters"
            params["product_name"] = product_name

        if product_url is not None:
            verify_url(product_url)
            params["product_url"] = product_url

        response = self._post_checkout(
            *self.encode(action, **params), redirect=False, **kwargs
        )

        next = response.next

        if next is None:
            result = {}
            if response.headers.get("Content-Type", "").startswith("application/json"):
                result = response.json()

            raise exception_factory(
                code=result.pop("err_code", None),
                description=result.pop("err_description", None),
                response=response,
                details=result,
            )

        return next.url

    def reports(
        self,
        /,
        date_from: Union[datetime, str, Number],
        date_to: Union[datetime, str, Number],
        *,
        format: Optional["Format"] = None,
    ) -> str:
        """
        Get an archive of recieved payments.

        Example to get a json archive for the last 30 days:
        >>> import json
        >>> from datetime import datetime, timedelta, UTC
        >>> from liqpy.client import Client
        >>> client = Client()
        >>> date_to = datetime.now(UTC)
        >>> date_from = date_to - timedelta(days=30)
        >>> data = client.reports(date_from, date_to, format="json")
        >>> data = json.loads(data)
        >>> print(len(data), "payments")

        [Documentaion](https://www.liqpay.ua/en/documentation/api/information/reports/doc)
        """

        kwargs = {
            "date_from": to_milliseconds(date_from),
            "date_to": to_milliseconds(date_to),
        }

        if format is not None:
            kwargs["resp_format"] = format

        response = self._post_request(*self.encode("reports", **kwargs))

        output: str = response.text
        error: dict | None = None

        content_type = response.headers.get("Content-Type", "")

        if content_type.startswith("application/json"):
            if format == "json":
                s = search(r'"data":(\[(.+?)\])', response.text)
                if s is not None:
                    output = s.group(1)
                else:
                    error = response.json()

            else:
                error = response.json()

        if error is None:
            return output
        else:
            raise exception_factory(
                code=error.pop("err_code"),
                description=error.pop("err_description"),
                response=response,
                details=error,
            )

    def data(self, /, order_id: str, info: str) -> dict:
        """
        Adding an info to already created payment.

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/data/doc)
        """
        return self.request("data", order_id=order_id, info=info)

    def receipt(
        self,
        /,
        order_id: str,
        email: str,
        *,
        payment_id: Optional[int] = None,
        language: Optional["Language"] = None,
    ) -> None:
        """
        Send a receipt to the customer.

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/ticket/doc)
        """
        kwargs = {}
        if payment_id is not None:
            kwargs["payment_id"] = payment_id

        if language is not None:
            kwargs["language"] = language

        self.request("receipt", order_id=order_id, email=email, **kwargs)

    def status(self, order_id: str, /) -> dict:
        """
        Get the status of a payment.

        [Documentation](https://www.liqpay.ua/en/documentation/api/information/status/doc)
        """
        return self.request("status", order_id=order_id)

    def callback(self, /, data: str, signature: str, *, verify: bool = True):
        """
        Verify and decode the callback data.

        Example:
        >>> from uuid import uuid4
        >>> from liqpy.client import Client
        >>> client = Client()
        >>> # get data and signature from webhook request body
        >>> order_id = str(uuid4())
        >>> data, signature = client.encode(
        >>>     action="pay",
        >>>     amount=1,
        >>>     order_id=order_id,
        >>>     description="Test Encoding",
        >>>     currency="USD",
        >>> )
        >>> # verify and decode data
        >>> result = client.callback(data, signature)
        >>> assert result["order_id"] == order_id
        >>> assert result["action"] == "pay"
        >>> assert result["amount"] == 1
        >>> assert result["currency"] == "USD"
        >>> assert result["description"] == "Test Encoding"

        [Documentation](https://www.liqpay.ua/en/documentation/api/callback)
        """
        result = self._callback(data, signature, verify=verify)
        version = result.get("version")

        if version != VERSION:
            logger.warning("Callback version mismatch: %s != %s", version, VERSION)

        return result
