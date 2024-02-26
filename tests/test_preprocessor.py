from datetime import datetime, timedelta
from json import loads

from pytest import fixture

from liqpy.api import Preprocessor
from liqpy.models.request import DetailAddenda

from tests import EXAMPLES_DIR


@fixture
def preprocessor():
    return Preprocessor()


def test_preprocess_report_timerange(preprocessor: Preprocessor):
    date_to = datetime.now()
    date_from = date_to - timedelta(days=30)

    r = {"date_to": date_to, "date_from": date_from}
    t = {k: int(v.timestamp() * 1000) for k, v in r.items()}

    preprocessor(r)
    assert r == t


def test_preprocess_dates(preprocessor: Preprocessor):
    t = {
        "expired_date": datetime.now(),
        "subscribe_date_start": datetime.now(),
        "letter_of_credit_date": datetime.now(),
    }

    r = {k: v.isoformat() for k, v in t.items()}
    preprocessor(r)
    assert r == t

    r = {k: v.timestamp() for k, v in t.items()}
    preprocessor(r)
    assert r == t


def test_preprocess_truthy(preprocessor: Preprocessor):
    r = {"subscribe": True, "letter_of_credit": True, "recurringbytoken": True}
    t = {k: 1 if v else None for k, v in r.items()}
    preprocessor(r)
    assert r == t

    r = {"subscribe": 1, "letter_of_credit": 1, "recurringbytoken": 1}
    t = r.copy()
    preprocessor(r)
    assert r == t

    r = {"subscribe": False, "letter_of_credit": False, "recurringbytoken": False}
    t = {k: 1 if v else None for k, v in r.items()}
    preprocessor(r)
    assert r == t

    r = {"subscribe": None, "letter_of_credit": None, "recurringbytoken": None}
    t = r.copy()
    preprocessor(r)
    assert r == t


def test_preprocess_verifycode(preprocessor: Preprocessor):
    r = {"verifycode": True}
    t = {"verifycode": "Y"}
    preprocessor(r)
    assert r == t

    r = {"verifycode": False}
    t = {"verifycode": None}
    preprocessor(r)
    assert r == t


def test_preprocess_detail_addenda(preprocessor: Preprocessor):
    with open(EXAMPLES_DIR / "dae.json") as f:
        data = loads(f.read())

    r = {"dae": data}
    t = {"dae": DetailAddenda.from_json(data)}
    preprocessor(r)

    assert r == t