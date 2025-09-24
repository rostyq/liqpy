"""
LiqPy - Command Line Interface for interacting with LiqPay API
"""

from typing import (
    get_args,
    get_origin,
    get_type_hints,
    cast,
    Any,
    Literal,
    Callable,
    NoReturn,
    Union,
    TypedDict,
)
from collections.abc import Iterable
from ipaddress import IPv4Address
from os import getenv, isatty, environ
from sys import stdin, stdout, exit, stderr
from functools import cached_property
from argparse import ArgumentParser, _ArgumentGroup
from pathlib import Path
from io import StringIO
from datetime import timedelta, datetime, UTC
from decimal import Decimal
from json.decoder import JSONDecodeError
from _colorize import can_colorize, get_theme, Syntax
from re import compile, sub, VERBOSE, Match

from liqpy import __version__
from liqpy.client import Client
from liqpy.api import sign
from liqpy.api.decoder import LiqpayDecoder
from liqpy.api.encoder import LiqpayEncoder, ReportEncoder
from liqpy.api.validation import LiqpayValidator
from liqpy.api.exceptions import LiqPayException

from liqpy import *
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
ReportFormat = Literal["csv", "json", "ndjson"]


_color_pattern = compile(
    r"""
    (?P<key>"(\\.|[^"\\])*")(?=:)           |
    (?P<string>"(\\.|[^"\\])*")             |
    (?P<number>NaN|-?Infinity|[0-9\-+.Ee]+) |
    (?P<boolean>true|false)                 |
    (?P<null>null)
""",
    VERBOSE,
)


def _colorize_json(json_str: str, theme: Syntax):
    def _replace_match_callback(match: Match) -> str:
        for group, color in [
            ("key", "definition"),
            ("string", "string"),
            ("number", "number"),
            ("boolean", "keyword"),
            ("null", "keyword"),
        ]:
            if m := match.group(group):
                return f"{theme[color]}{m}{theme.reset}"
        return match.group()

    return sub(_color_pattern, _replace_match_callback, json_str)


class OrderOrPaymentId(TypedDict):
    order_id: str | None
    payment_id: int | None


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


def handle_report_date(value: str) -> str | int | float | DateTuple:
    return (
        "-" + d if isinstance(d := handle_date(value), str) and d.startswith("P") else d
    )


def handle_opid(value: str) -> str | int:
    if value.isdecimal():
        return int(value)
    else:
        return value


def add_arguments_from_typed_dict(
    p: ArgumentParser | _ArgumentGroup,
    t: type,
    json: Callable[[str], Any],
    exclude: set[str] = set(),
):
    hints = get_type_hints(t).items()
    for name, hint in [
        (k, v) for k, v in sorted(hints, key=lambda v: v[0]) if k not in exclude
    ]:
        arg_name = f"--{name.replace('_', '-')}"

        if isinstance(hint, type):
            p.add_argument(arg_name, type=hint, required=True)

        elif get_origin(hint) is Literal:
            p.add_argument(arg_name, choices=get_args(hint), required=True)

        else:
            type_args = [arg for arg in get_args(hint)]
            required = type(None) not in type_args
            type_args = [arg for arg in type_args if arg is not type(None)]

            if len(type_args) == 2 and type_args[0] is bool:
                p.add_argument(
                    arg_name,
                    choices=("true", *get_args(type_args[1])),
                    required=required,
                )

            elif (origin := get_origin(arg_type := type_args[0])) is Literal:
                p.add_argument(arg_name, choices=get_args(arg_type), required=required)

            elif origin is Iterable:
                type_args = get_args(arg_type)

                if all(map(lambda a: get_origin(a) is Literal, type_args)):
                    p.add_argument(
                        arg_name,
                        nargs="+" if required else "*",
                        choices=[item for arg in type_args for item in get_args(arg)],
                        required=required,
                    )
                else:
                    type_args = [item for arg in type_args for item in get_args(arg)]

                    if type_args and isinstance(get_type_hints(type_args[0]), dict):
                        p.add_argument(arg_name, type=json, required=required)

                    else:
                        raise NotImplementedError(
                            f"Unsupported Iterable type args: {type_args}"
                        )

            elif arg_type is bool:
                assert required is False
                p.add_argument(arg_name, action="store_true")

            elif arg_type in (str, int, Decimal, IPv4Address):
                p.add_argument(arg_name, type=arg_type, required=required)

            elif arg_type is datetime:
                if name in ("date_from", "date_to"):
                    p.add_argument(arg_name, type=handle_report_date, required=required)
                else:
                    p.add_argument(arg_name, type=handle_date, required=required)

            elif isinstance(get_type_hints(arg_type), dict):
                p.add_argument(arg_name, type=json, required=required)

            else:
                raise NotImplementedError(f"Unsupported argument type: {arg_type}")


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
    def __init__(self):
        self.ap = ap = ArgumentParser(
            description=__doc__, color=isatty(stdout.fileno())
        )
        self.validator = CustomValidator(ap.error)
        self.encoder = LiqpayEncoder(self.validator)
        self.decoder = CustomDecoder(ap.error)
        self.reporter = ReportEncoder()

        # global options
        ap.add_argument(
            "--version", action="version", version=f"{__package__} {__version__}"
        )
        ap.add_argument(
            "-i",
            "--input",
            dest="input",
            type=Path,
            help="input file to read as last positional argument (default: standard input)",
        )
        ap.add_argument(
            "-o",
            "--output",
            dest="output",
            type=Path,
            help="output file (default: standard output)",
        )
        ap.add_argument(
            "-a",
            "--append",
            dest="mode",
            default="w",
            action="store_const",
            const="a",
            help="append to output file instead of overwriting",
        )
        ap.add_argument(
            "-e", "--env-file", type=Path, help="load environment variables from file"
        )

        pk_ap = pap = ArgumentParser(add_help=False)
        pubkey_arg = pap.add_argument(
            "-u",
            "--public-key",
            help="set public key (required, env: LIQPAY_PUBLIC_KEY)",
        )
        prikey_arg = pap.add_argument(
            "-p",
            "--private-key",
            help="set private key (required, env: LIQPAY_PRIVATE_KEY)",
        )

        # subcommands
        spa = ap.add_subparsers(
            description="Available commands", dest="command", metavar="command"
        )

        # data actions
        sp = spa.add_parser(
            "sign",
            help="sign data using the private key",
            description="Sign input data using the PRIVATE_KEY and output the base64-encoded signature.",
        )
        sp.add_argument("input", nargs="?", help="data to sign")
        sp._add_action(prikey_arg)
        sp = spa.add_parser(
            "encode",
            help="encode and validate request JSON to base64",
            description="Encode and validate request JSON data to base64 format. "
            "Requires PUBLIC_KEY for the request data.",
        )
        sp.add_argument("input", nargs="?", help="JSON data to encode")
        sp._add_action(pubkey_arg)
        # add_arguments_from_typed_dict(
        #     sp.add_argument_group(title="params"),
        #     LiqpayRequest,
        #     self.decoder.decode,
        #     exclude={"public_key", "version"},
        # )
        spa.add_parser(
            "form",
            help="prepare data and signature for HTML form",
            description="Prepare base64-encoded data and signature for HTML form submission. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for signing the data and "
            "outputs the signature followed by the data, separated by two newlines.",
            parents=[pk_ap],
        ).add_argument("input", nargs="?", help="JSON data to prepare")
        spa.add_parser(
            "payload",
            help="prepare URL-encoded payload for HTTP request",
            description="Prepare URL-encoded payload for HTTP request. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for signing the data "
            "and outputs the payload as a single line string.",
            parents=[pk_ap],
        ).add_argument("input", nargs="?", help="JSON data to prepare")

        # request action
        action_choices = [
            value for item in get_args(LiqpayAction) for value in get_args(item)
        ]
        sp = spa.add_parser(
            "request",
            help="request an action",
            description="Make a request to the API for a specific action. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
            epilog="List of actions: " + ", ".join(action_choices) + ".",
            parents=[pk_ap],
        )
        sp.add_argument(
            "action",
            help="action to perform",
            choices=action_choices,
            metavar="action",
        )
        sp.add_argument("input", nargs="?", help="request data as JSON string")

        # reports
        sp = spa.add_parser(
            "reports",
            help="download payment reports",
            description="Download payment reports in chunks over a specified date range. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication. "
            "Outputs the report data in the specified format: CSV, JSON or JSON lines (NDJSON).",
            parents=[pk_ap],
        )
        sp.add_argument("date_from", type=handle_report_date)
        sp.add_argument(
            "date_to",
            nargs="?",
            type=handle_report_date,
            default=timedelta(),
            help="start date as ISO 8601 string datetime/duration, date string as YYYY-MM-DD, "
            "integer timestamp in milliseconds or float timestamp in seconds (default: now)",
        )
        sp.add_argument(
            "-t",
            "--timespan",
            type=parse_isoduration,
            default=timedelta(days=30),
            help="timespan ISO 8601 duration for each report chunk (default: P30D)",
        )
        sp.add_argument(
            "-f",
            "--format",
            choices=get_args(ReportFormat),
            default="csv",
            help="report output format (default: csv)",
        )
        sp.add_argument(
            "--skip-header",
            "--no-header",
            dest="skip_header",
            default=False,
            action="store_true",
            help="skip CSV header row (only for --format csv)",
        )

        # status
        sp = spa.add_parser(
            "status",
            help="check payment status",
            description="Check the status of a payment using either the order ID or payment ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
            parents=[pk_ap],
        )
        sp.add_argument("id", type=handle_opid, help="order or payment ID to check")
        sp.add_argument(
            "--order",
            dest="is_order_id",
            default=False,
            action="store_true",
            help="treat input only as order ID",
        )

        # data
        sp = spa.add_parser(
            "data",
            help="add information about the payment",
            description="Add additional information about the payment using either the order ID or payment ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
            parents=[pk_ap],
        )
        sp.add_argument(
            "id", type=handle_opid, help="order or payment ID to set data for"
        )
        sp.add_argument(
            "--order",
            dest="is_order_id",
            default=False,
            action="store_true",
            help="treat id only as order",
        )
        sp.add_argument("input", nargs="?", help="information to set for the payment")

        # subscribe_update
        sp = spa.add_parser(
            "subscribe_update",
            aliases=["subscription"],
            help="update active subscription",
            description="Update an active subscription for a specific order ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
            parents=[pk_ap],
        )
        sp.add_argument(
            "--id",
            dest="order_id",
            help="order ID of the subscription to update",
            required=True,
        )
        sp.add_argument(
            "--amount",
            type=Decimal,
            help="new amount for the subscription",
            required=True,
        )
        sp.add_argument(
            "--currency",
            choices=get_args(Currency),
            help="new currency for the subscription",
            required=True,
        )
        sp.add_argument("input", nargs="?", help="description for the subscription")

        # unsubscribe
        sp = spa.add_parser(
            "unsubscribe",
            aliases=["unsub"],
            help="unsubscribe from recurring payments",
            description="Unsubscribe from recurring payments for a specific order ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
            parents=[pk_ap],
        ).add_argument("id", help="order ID to unsubscribe")

        # refund
        sp = spa.add_parser(
            "refund",
            help="issue a refund for a payment",
            description="Issue a refund for a specific order or payment ID. "
            "Requires both PUBLIC_KEY and PRIVATE_KEY for authentication.",
            parents=[pk_ap],
        )
        sp.add_argument("id", type=handle_opid, help="order or payment ID to refund")
        sp.add_argument(
            "--amount",
            type=Decimal,
            default=None,
            help="amount to refund (default: full)",
            required=False,
        )
        sp.add_argument(
            "--order",
            dest="is_order_id",
            default=False,
            action="store_true",
            help="treat id only as order",
        )

        self.args = ap.parse_args()

    def _err_required(self, *names: str):
        return self.ap.error(
            f"the following arguments are required: " + ", ".join(names)
        )

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

    def _load_env(self):
        if not isinstance(p := self.args.env_file, Path):
            return

        with p.open() as f:
            while line := f.readline().strip():
                if not line.startswith("LIQPAY_"):
                    continue
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                environ.setdefault(key, value)

    def input(self, prompt: str | None = None):
        if isinstance(argin := self.args.input, Path):
            return argin.open()
        elif argin is None:
            return (
                stdin
                if not isatty(stdin.fileno())
                else StringIO(input(prompt or "input> "))
            )
        else:
            return StringIO(argin)

    def _read_input(self, prompt: str | None = None):
        with self.input(prompt) as input:
            return input.read().strip()

    def _read_params(self, prompt: str | None = None):
        with self.input(prompt) as input:
            s = input.read().strip()
            return cast(LiqpayParams, self.decoder.decode(s) if s else {})

    def _read_request(self, public_key: str | None = None, prompt: str | None = None):
        with self.input(prompt) as input:
            s = input.read().strip()
            params = self.decoder.decode(s) if s else {}
            return cast(
                LiqpayRequest,
                {**params, "public_key": public_key or self.public_key},
            )

    def output(self):
        return open(o, self.args.mode) if (o := self.args.output) else stdout

    def client(self):
        public_key, private_key = self._keys()
        try:
            return Client(
                public_key, private_key, encoder=self.encoder, decoder=self.decoder
            )
        except ValueError as e:
            self.ap.error(str(e))

    def _order_or_payment_id(self, value: str | int) -> OrderOrPaymentId:
        if not self.args.is_order_id and isinstance(value, int):
            return {"order_id": None, "payment_id": int(value)}
        else:
            return {"order_id": str(value), "payment_id": None}

    def _run(self):
        prompt = "JSON>"
        match self.command:
            case "encode":
                yield self.encoder(self._read_request(prompt=prompt)).decode()

            case "sign":
                yield sign(
                    self._read_input().encode(), self.private_key.encode()
                ).decode()

            case "form":
                public_key, private_key = self._keys()
                data, signature = self.encoder.form(
                    private_key.encode(), self._read_request(public_key, prompt=prompt)
                )
                yield signature.decode()
                yield "\n\n"
                yield data.decode()

            case "payload":
                public_key, private_key = self._keys()
                yield self.encoder.payload(
                    private_key.encode(), self._read_request(public_key, prompt=prompt)
                ).decode()

            case "reports":
                with self.client() as client:
                    yield from self._run_reports(client)

            case _:
                with self.client() as client:
                    if (result := self._run_client(client)) is not None:
                        yield self.reporter.encode(result)

    def _run_reports(self, client: Client):
        timeout = 30

        date_from = to_datetime(self.args.date_from)
        date_to = to_datetime(self.args.date_to)

        step: timedelta = self.args.timespan
        format: Literal["csv", "json", "ndjson"] = self.args.format

        if step <= timedelta(milliseconds=0):
            self.ap.error("timespan must be positive")
        if date_from >= date_to:
            self.ap.error("date_from must be earlier than date_to")

        chunk_date_from = date_from
        while (
            chunk_date_to := min(date_to, chunk_date_from + step)
        ) != chunk_date_from:
            assert chunk_date_from < chunk_date_to

            is_first_chunk = chunk_date_from == date_from
            is_last_chunk = chunk_date_to == date_to

            if format == "csv":
                result = client.reports(
                    date_from=chunk_date_from,
                    date_to=chunk_date_to,
                    resp_format="csv",
                    timeout=timeout,
                )
                if is_first_chunk and not self.args.skip_header:
                    yield result
                else:
                    next(lines := iter(result.splitlines(keepends=True)))
                    yield from lines
            else:
                result = client.payments(
                    date_from=chunk_date_from, date_to=chunk_date_to, timeout=timeout
                )

                if format == "json":
                    last_index = len(result) - 1
                    not_empty = last_index >= 0

                    if is_first_chunk:
                        yield "["
                    elif not_empty:
                        yield ","

                    items = iter(result)
                    for _ in range(last_index):
                        yield self.reporter.encode(next(items))
                        yield ","

                    if not_empty:
                        yield self.reporter.encode(next(items))

                    if is_last_chunk:
                        yield "]"

                else:  # ndjson
                    for item in result:
                        yield self.reporter.encode(item)
                        yield "\n"

            chunk_date_from = chunk_date_to + timedelta(milliseconds=0)

    def _run_client(self, client: Client):
        match self.command:
            case "request":
                return client.request(
                    action=self.args.action, **self._read_params("JSON> ")
                )

            case "status":
                return client.status(**self._order_or_payment_id(self.args.id))

            case "data":
                return client.data(
                    **self._order_or_payment_id(self.args.id),
                    info=self._read_input("info> "),
                )

            case "unsubscribe" | "unsub":
                return client.unsubscribe(self.args.id)

            case "refund":
                return client.refund(
                    **self._order_or_payment_id(self.args.id),
                    amount=self.args.amount,
                )

            case "subscribe_update" | "subscription":
                return client.subscription(
                    order_id=self.args.id,
                    amount=self.args.amount,
                    currency=self.args.currency,
                    description=self._read_input("description> "),
                )

            case command if command in [
                value for item in get_args(Command) for value in get_args(item)
            ]:
                raise NotImplementedError(f"Command not yet implemented: {command}")

            case _:
                self.ap.error(f"unknown command: {self.command}")

    def run(self):
        self._load_env()

        first_chunk = next(other_chunks := self._run())
        with self.output() as output:
            if "json" in getattr(self.args, "format", "") and can_colorize(file=output):
                t = get_theme(tty_file=output).syntax
                write = lambda s: output.write(_colorize_json(s, t))
            else:
                write = output.write

            write(first_chunk)

            for chunk in other_chunks:
                write(chunk)

            output.flush()

        exit(0)


try:
    with NOW.set(datetime.now(UTC)):
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
