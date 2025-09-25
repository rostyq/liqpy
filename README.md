# LiqPy

LiqPy -- unofficial python library for [LiqPay API](https://www.liqpay.ua/doc).

> _Is it **production ready**?_
>
> Short answer: Well, yes, but actually no.
>
> Long answer: It depends on what production readiness means for you.
> Implementation still lacks some LiqPay's functionality and tests coverage,
> but I, personally, use it in production.
> It gets work done in a most pythonic way I see it.

## Installation

```shell
pip install liqpy
```

## Basic Usage

Get `public_key` and `private_key` from LiqPay and create a checkout link:

```python
from liqpy.client import Client

# env variables for keys are LIQPAY_PUBLIC_KEY and LIQPAY_PRIVATE_KEY
client = Client(public_key=..., private_key=...)

checkout_link = client.checkout(
    action="pay",
    order_id=...,
    amount=1,
    currency="USD",
    description="Payment Example",
    # set server_url for handling a callback
    # server_url=...
)
print(checkout_link)
```

## Handle Callback

Handle [callback from LiqPay](https://www.liqpay.ua/en/doc/api/callback) after checkout on your server (`server_url`):

```python
from urllib.parse import parse_qs
from liqpy.api.exceptions import LiqPayRequestException

# request body content type is application/x-www-form-urlencoded
def handle_callback(body: str):
    query = parse_qs(body)
    data, signature = query["data"][0], query["signature"][0]
    try:
        result = client.callback(data, signature)
        print(result)
    except LiqPayRequestException:
        print("LiqPay callback verification failed.")
```

See [`readme.ipynb`](./readme.ipynb) for more examples.
