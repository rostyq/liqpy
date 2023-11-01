# LiqPy

LiqPy -- unofficial python library for [LiqPay API](https://www.liqpay.ua/documentation/api/).

## Installation

```shell
pip install liqpy
```

## Basic Usage

Create checkout link:

```python
from uuid import uuid4
from liqpy.client import Client

client = Client(public_key=..., private_key=...)

client.checkout(
    action="pay",
    order_id=str(uuid4()),
    amount=1,
    currency="USD",
    description="Payment Example",
    server_url=...
)
```

Handle [callback from LiqPay](https://www.liqpay.ua/en/documentation/api/callback) after checkout on your server (`server_url`):

```python
def handle_callback(data: str, signature: str):
    try:
        callback = client.callback(data, signature)
        print(callback)
    except AssertionError as e:
        print("LiqPay callback verification failed.", e)
```


## Development

Create Python environment (optional):

```shell
python -m env env
```

Install requirements:

```shell
pip install -r requirements.txt -r requirements-dev.txt
```


### Setup credentials

Get your `public_key` and `private_key` from LiqPay.

Write keys to `.env` file as follows:

```shell
LIQPAY_PUBLIC_KEY=${public_key}
LIQPAY_PRIVATE_KEY=${private_key}
```


### Local webhook handler

Bind localhost port to the Internet:

```shell
ngrok http 8000
```

Look for the similar line in console:

```
Forwarding https://7kh6-111-111-111-111.ngrok-free.app -> http://localhost:8000 
```

Add server URL to `.env` file:

```
SERVER_URL=https://7kh6-111-111-111-111.ngrok-free.app
```

Start local webhook handler:

```shell
python -m tests.server
```

Now you can recieve callbacks after requesting LiqPay API.

```python
from os import environ
from dotenv import load_env
from liqpay.client import Client

client = Client()

client.request(
    action=...,
    order_id=...,
    amount=...,
    server_url=environ.get("SERVER_URL")
)
```

See [`readme.ipynb`](./readme.ipynb) for more examples.