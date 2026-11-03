"""Tests for the validation rules and the API.  Run:  python -m pytest -q"""
import pytest

from server import app
from validation import parse_price, validate_email, validate_purchase

VALID = {
    "product_id": "SKU-1001",
    "description": "Wireless mouse",
    "customer_name": "Ada Lovelace",
    "customer_email": "ada@example.com",
    "price": "49.99",
    "is_online": True,
}


@pytest.mark.parametrize("email", ["ada@example.com", "a.b+tag@mail.co.uk", "x_y@sub-domain.io"])
def test_valid_emails(email):
    assert validate_email(email) is None


@pytest.mark.parametrize("email", ["", "ada", "ada@", "@example.com", "ada@example",
                                   "ada@@example.com", "ada @example.com", "ada..b@example.com"])
def test_invalid_emails(email):
    assert validate_email(email) is not None


@pytest.mark.parametrize("raw,expected", [("1000", "1000.00"), ("1000.00", "1000.00"),
                                          ("$999.99", "999.99"), ("1,000.00", "1000.00"), ("0.01", "0.01")])
def test_valid_prices(raw, expected):
    price, err = parse_price(raw)
    assert err is None and str(price) == expected


@pytest.mark.parametrize("raw", ["", "abc", "0", "-5", "1000.01", "1500", "10.999", "NaN", "inf"])
def test_invalid_prices(raw):
    assert parse_price(raw)[1] is not None


def test_validate_purchase_ok():
    assert validate_purchase(VALID) == {}


def test_validate_purchase_reports_each_field():
    errors = validate_purchase({"is_online": "yes"})
    assert set(errors) == {"product_id", "description", "customer_name",
                           "customer_email", "price", "is_online"}


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()


def test_post_valid_purchase(client):
    resp = client.post("/api/purchases", json=VALID)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["success"] and body["purchase"]["price"] == "49.99"
    assert body["purchase"]["channel"] == "Online"


def test_post_in_store(client):
    resp = client.post("/api/purchases", json={**VALID, "is_online": False})
    assert resp.get_json()["purchase"]["channel"] == "In store"


def test_server_rejects_over_limit(client):
    resp = client.post("/api/purchases", json={**VALID, "price": "1000.01"})
    assert resp.status_code == 422
    assert "price" in resp.get_json()["errors"]


def test_server_rejects_non_json(client):
    resp = client.post("/api/purchases", data="not json", content_type="text/plain")
    assert resp.status_code == 400
