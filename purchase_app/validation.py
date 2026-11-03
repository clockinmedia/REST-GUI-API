"""Validation rules for a purchase. The client and the server both use this module.

The client validates so the user gets instant feedback. The server validates
again because a client can never be trusted on its own.
"""
import re
from decimal import Decimal, InvalidOperation

MAX_PRICE = Decimal("1000.00")

# A practical email check: local@domain.tld with no spaces and a TLD of 2+ letters.
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
PRODUCT_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,20}$")


def validate_email(email: str) -> str | None:
    """Return an error message, or None if the email is valid."""
    email = (email or "").strip()
    if not email:
        return "Email is required."
    if ".." in email or not EMAIL_RE.match(email):
        return "Email format is invalid (expected name@example.com)."
    return None


def parse_price(raw) -> tuple[Decimal | None, str | None]:
    """Parse and check a price. Returns (price, error)."""
    text = str(raw if raw is not None else "").strip().replace("$", "").replace(",", "")
    if not text:
        return None, "Price is required."
    try:
        price = Decimal(text)
    except InvalidOperation:
        return None, "Price must be a number."
    if not price.is_finite():
        return None, "Price must be a number."
    if price <= 0:
        return None, "Price must be greater than $0.00."
    if price > MAX_PRICE:
        return None, f"Price must be ≤ ${MAX_PRICE:,.2f}."
    if price.as_tuple().exponent < -2:
        return None, "Price can have at most 2 decimal places."
    return price.quantize(Decimal("0.01")), None


def validate_purchase(data: dict) -> dict[str, str]:
    """Validate all fields. Returns {field_name: error_message}; empty means valid."""
    errors: dict[str, str] = {}

    product_id = str(data.get("product_id", "")).strip()
    if not product_id:
        errors["product_id"] = "Product ID is required."
    elif not PRODUCT_ID_RE.match(product_id):
        errors["product_id"] = "Product ID: letters, digits and dashes only (max 20)."

    description = str(data.get("description", "")).strip()
    if not description:
        errors["description"] = "Description is required."
    elif len(description) > 200:
        errors["description"] = "Description must be 200 characters or fewer."

    if not str(data.get("customer_name", "")).strip():
        errors["customer_name"] = "Customer name is required."

    if (err := validate_email(data.get("customer_email", ""))):
        errors["customer_email"] = err

    _, err = parse_price(data.get("price"))
    if err:
        errors["price"] = err

    if not isinstance(data.get("is_online"), bool):
        errors["is_online"] = "is_online must be true or false."

    return errors
