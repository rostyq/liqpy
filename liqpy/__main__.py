"""
LiqPy - Command Line Interface for interacting with LiqPay API
"""

from typing import Any, Literal, get_args, cast, Callable, NoReturn, Union
from os import getenv, isatty, environ
from sys import stdin, stdout, exit, stderr
from functools import cached_property
from argparse import ArgumentParser
from pathlib import Path
from io import StringIO
from datetime import timedelta
from decimal import Decimal
from json.decoder import JSONDecodeError

from liqpy import __version__
from liqpy.client import Client
from liqpy.api import sign
from liqpy.api.decoder import LiqpayDecoder
from liqpy.api.encoder import LiqpayEncoder, ReportEncoder
from liqpy.api.validation import LiqpayValidator
from liqpy.api.exceptions import LiqPayException

from liqpy.convert import *
from liqpy.types import *
from liqpy.types.request import *


ErrorFn = Callable[[str], NoReturn]
DataAction = Literal[
    "sign",
    "encode",
    "form",
    "payload",
    "request",
]
Command = Union[DataAction, LiqpayAction]


def handle_date(value: str) -> str | int | float | DateTuple:
    if value.isdecimal():
        return int(value)
    elif value.replace(".", "").isdecimal():
        return float(value)
    elif value.startswith(("P", "-P")):
        return value
    elif value.replace("-", "").isdecimal() and len(parts := value.split("-")) == 3:
        y, d, m = map(int, parts)
        return (y, d, m)
    else:
        return value


class CustomDecoder(LiqpayDecoder):
    def __init__(self, error: ErrorFn):
        super().__init__()
        self.error = error

    def decode(self, s: str):
        try:
            return super().decode(s)
        except JSONDecodeError as e:
            self.error(f"Invalid JSON input. {e}")


class CustomValidator(LiqpayValidator):
    def __init__(self, error: ErrorFn):
        super().__init__()
        self.error = error

    def __call__(self, obj: Any) -> Any:
        try:
            return super().__call__(obj)
        except* (ValueError, TypeError) as g:
            self.error(g.message + "\n" + "\n".join(str(err) for err in g.exceptions))


class App:
    def __init__(self) -> None:
        self.ap = ap = ArgumentParser(prog=__package__, description=__doc__)
        ap.add_argument(
            "--version", action="version", version=f"{__package__} {__version__}"
        )

        # global options
        ag = ap.add_argument_group("data", "input and output data")
        ag.add_argument(
            "-i",
            "--input",
            type=Path,
            help="output file (default: standard input)",
        )
        ag.add_argument(
            "-o",
            "--output",
            type=Path,
            help="output file (default: standard output)",
        )
        ag.add_argument(
            "-e", "--env-file", type=Path, help="load environment variables from file"
        )

        ag = ap.add_argument_group(
            "authentication", description="API authentication keys"
        )
        ag.add_argument("--public-key", help="set public key (env: LIQPAY_PUBLIC_KEY)")
        ag.add_argument(
            "--private-key", help="set private key (env: LIQPAY_PRIVATE_KEY)"
        )

        # subcommands
        subs = ap.add_subparsers(description="Available commands", dest="command")

        # data actions
        subs.add_parser(
            "sign",
            help="sign data using the private key",
            description="Sign input data using the PRIVATE_KEY and output the base64-encoded signature.",
        ).add_argument("input", nargs="?", help="data to sign")
        subs.add_parser(
            "encode",
            help="encode and validate request JSON to base64",
            description="Encode and validate request JSON data to base64 format. "
            "Requires PUBLIC_KEY for the request data.",
        ).add_argument("input", nargs="?", help="JSON data to encode")
        subs.add_parser(
            "form",
            help="prepare data and signature for HTML form",
            description="Prepare base64-encoded data and signature for HTML form submission. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for signing the data and "
            "outputs the signature followed by the data, separated by two newlines.",
        ).add_argument("input", nargs="?", help="JSON data to prepare")
        subs.add_parser(
            "payload",
            help="prepare URL-encoded payload for HTTP request",
            description="Prepare URL-encoded payload for HTTP request. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for signing the data "
            "and outputs the payload as a single line string.",
        ).add_argument("input", nargs="?", help="JSON data to prepare")

        # request action
        sub = subs.add_parser(
            "request",
            help="request an action",
            description="Make a request to the API for a specific action. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
        )
        sub.add_argument(
            "action",
            help="action to perform",
            choices=[
                value for item in get_args(LiqpayAction) for value in get_args(item)
            ],
        )
        sub.add_argument("input", nargs="?", help="request data as JSON string")

        # reports
        sub = subs.add_parser(
            "reports",
            help="download payment reports",
            description="Download payment reports in chunks over a specified date range. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication. "
            "Outputs the report data in the specified format (CSV or NDJSON).",
        )
        sub.add_argument(
            "--date-from",
            dest="date_from",
            type=handle_date,
            help="start date as ISO 8601 string or integer timestamp in milliseconds",
            required=True,
        )
        sub.add_argument(
            "--date-to",
            dest="date_to",
            type=handle_date,
            default=timedelta(),
            help="start date as ISO 8601 string or integer timestamp in milliseconds (default: now)",
        )
        sub.add_argument(
            "--timespan",
            type=parse_isoduration,
            default=timedelta(days=30),
            help="timespan ISO 8601 duration for each report chunk (default: P30D)",
        )
        sub.add_argument(
            "--format",
            choices=["csv", "json", "ndjson"],
            default="csv",
            help="report output format (default: csv, other: json, ndjson)",
        )

        # status
        sub = subs.add_parser(
            "status",
            help="check payment status",
            description="Check the status of a payment using either the order ID or payment ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
        )
        sub.add_argument(
            "--order-id", help="order ID of the payment to check", required=False
        )
        sub.add_argument(
            "--payment-id", type=int, help="payment ID to check", required=False
        )

        # data
        sub = subs.add_parser(
            "data",
            help="add information about the payment",
            description="Add additional information about the payment using either the order ID or payment ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
        )
        sub.add_argument(
            "--order-id", help="order ID of the payment to set data for", required=False
        )
        sub.add_argument(
            "--payment-id", type=int, help="payment ID to set data for", required=False
        )
        sub.add_argument("input", nargs="?", help="information to set for the payment")

        # subscribe_update
        sub = subs.add_parser(
            "subscribe_update",
            aliases=["subscription"],
            help="update active subscription",
            description="Update an active subscription for a specific order ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
        )
        sub.add_argument(
            "--order-id", help="order ID of the subscription to update", required=True
        )
        sub.add_argument(
            "--amount",
            type=Decimal,
            help="new amount for the subscription",
            required=True,
        )
        sub.add_argument(
            "--currency",
            choices=("UAH", "USD", "EUR"),
            help="new currency for the subscription",
            required=True,
        )
        sub.add_argument("input", nargs="?", help="description for the subscription")

        # unsubscribe
        sub = subs.add_parser(
            "unsubscribe",
            aliases=["unsub"],
            help="unsubscribe from recurring payments",
            description="Unsubscribe from recurring payments for a specific order ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
        ).add_argument("--order-id", help="order ID to unsubscribe", required=True)

        # refund
        sub = subs.add_parser(
            "refund",
            help="issue a refund for a payment",
            description="Issue a refund for a specific payment ID. "
            "Provide either the ORDER_ID or PAYMENT_ID, and optionally an amount to refund. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
        )
        sub.add_argument(
            "--order-id", help="order ID of the payment to refund", required=False
        )
        sub.add_argument(
            "--payment-id", type=int, help="payment ID to refund", required=False
        )
        sub.add_argument(
            "--amount",
            type=Decimal,
            default=None,
            help="amount to refund (default: full)",
            required=False,
        )

        self.encoder = LiqpayEncoder(CustomValidator(ap.error))
        self.reporter = ReportEncoder()
        self.decoder = CustomDecoder(ap.error)

    def _err_required(self, *names: str):
        return self.ap.error(
            f"the following arguments are required: " + ", ".join(names)
        )

    @cached_property
    def args(self):
        return self.ap.parse_args()

    @cached_property
    def command(self) -> Command:
        return self.args.command

    def _public_key(self) -> str | None:
        return self.args.public_key or getenv("LIQPAY_PUBLIC_KEY")

    @cached_property
    def public_key(self) -> str:
        return pk if (pk := self._public_key()) else self._err_required("PUBLIC_KEY")

    def _private_key(self) -> str | None:
        return self.args.private_key or getenv("LIQPAY_PRIVATE_KEY")

    @cached_property
    def private_key(self) -> str:
        return pk if (pk := self._private_key()) else self._err_required("PRIVATE_KEY")

    def input(self):
        if self.command in ("reports", "status", "unsubscribe", "refund"):
            return StringIO("")
        elif isinstance(argin := self.args.input, Path):
            return argin.open()
        elif argin is None:
            return (
                open(stdin.fileno(), "r")
                if not isatty(stdin.fileno())
                else StringIO(input("liqpay input> "))
            )
        else:
            return StringIO(argin)

    def output(self):
        return open(o, "w") if (o := self.args.output) else stdout

    def _keys(self):
        public_key, private_key = self._public_key(), self._private_key()
        match (public_key, private_key):
            case (None, None):
                self._err_required("PUBLIC_KEY", "PRIVATE_KEY")
            case (None, _):
                self._err_required("PUBLIC_KEY")
            case (_, None):
                self._err_required("PRIVATE_KEY")
        return public_key, private_key

    def client(self):
        public_key, private_key = self._keys()
        try:
            return Client(
                public_key, private_key, encoder=self.encoder, decoder=self.decoder
            )
        except ValueError as e:
            self.ap.error(str(e))

    def request(self, input: str, public_key: str | None = None):
        return cast(
            LiqpayRequest,
            {**self.decoder.decode(input), "public_key": public_key or self.public_key},
        )

    def _load_env(self):
        if not isinstance(p := self.args.env_file, Path):
            return

        with p.open() as f:
            while line := f.readline().strip():
                if line.startswith("LIQPAY_"):
                    key, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    environ.setdefault(key, value)

    def _run_client(self, input: str, client: Client):
        match self.command:
            case "request":
                return client.request(
                    action=self.args.action, **self.decoder.decode(input)
                )

            case "status":
                return client.status(
                    order_id=self.args.order_id, payment_id=self.args.payment_id
                )

            case "data":
                return client.data(
                    order_id=self.args.order_id,
                    payment_id=self.args.payment_id,
                    info=input,
                )

            case "unsubscribe" | "unsub":
                return client.unsubscribe(self.args.order_id)

            case "refund":
                return client.refund(
                    order_id=self.args.order_id,
                    payment_id=self.args.payment_id,
                    amount=self.args.amount,
                )

            case "subscribe_update" | "subscription":
                return client.subscription(
                    order_id=self.args.order_id,
                    amount=self.args.amount,
                    currency=self.args.currency,
                    description=input,
                )

            case command if command in [
                value for item in get_args(Command) for value in get_args(item)
            ]:
                raise NotImplementedError(f"Command not yet implemented: {command}")

            case _:
                self.ap.error(f"unknown command: {self.command}")

    def _run_reports(self, client: Client):
        timeout = 30

        date_from = to_datetime(self.args.date_from)
        date_to = to_datetime(self.args.date_to)

        step: timedelta = self.args.timespan
        format: Literal["csv", "json", "ndjson"] = self.args.format

        chunk_date_from = date_from
        while chunk_date_from < min(date_to, chunk_date_to := chunk_date_from + step):
            is_first = chunk_date_from == date_from
            is_last = chunk_date_to >= date_to

            if format == "csv":
                yield from client.reports(
                    date_from=chunk_date_from,
                    date_to=chunk_date_to,
                    resp_format="csv",
                    timeout=timeout,
                ).splitlines(keepends=True)[0 if is_first else 1 :]
            else:
                items = client.payments(
                    date_from=chunk_date_from, date_to=chunk_date_to, timeout=timeout
                )

                if format == "json":
                    if is_first:
                        yield "["
                    for item in items[: -2 if is_last else -1]:
                        yield self.reporter.encode(item)
                        yield ","
                    if is_last:
                        yield self.reporter.encode(items[-1])
                        yield "]"

                else:  # ndjson
                    for item in items:
                        yield self.reporter.encode(item)
                        yield "\n"

            chunk_date_from = chunk_date_to

    def _run(self, input: str):
        self._load_env()

        match self.command:
            case "encode":
                yield self.encoder(self.request(input)).decode()

            case "sign":
                yield sign(input.encode(), self.private_key.encode()).decode()

            case "form":
                public_key, private_key = self._keys()
                data, signature = self.encoder.form(
                    private_key.encode(), self.request(input, public_key)
                )
                yield signature.decode()
                yield "\n\n"
                yield data.decode()

            case "payload":
                public_key, private_key = self._keys()
                yield self.encoder.payload(
                    private_key.encode(), self.request(input, public_key)
                ).decode()

            case "reports":
                with self.client() as client:
                    yield from self._run_reports(client)

            case _:
                with self.client() as client:
                    if (result := self._run_client(input, client)) is not None:
                        yield self.reporter.encode(result)

    def run(self):
        with self.input() as input, self.output() as output:
            for chunk in self._run(input.read()):
                output.write(chunk)
                output.flush()

        exit(0)


try:
    App().run()

except LiqPayException as e:
    print(f"Error {e.code}: {e}", file=stderr)
    # for key, value in e.details.items():
    #     print(f"{key}: {value}", file=stderr)
    exit(-1)

except NotImplementedError as e:
    print(str(e), file=stderr)
    exit(-1)

except KeyboardInterrupt:
    exit(130)
