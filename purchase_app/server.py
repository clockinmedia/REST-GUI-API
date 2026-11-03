"""Flask API that receives purchase JSON from the desktop client.

Run:  python server.py      (listens on http://127.0.0.1:5000)
"""
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from validation import parse_price, validate_purchase

app = Flask(__name__)
PURCHASES: list[dict] = []  # in-memory store, good enough for a demo


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/purchases")
def create_purchase():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, message="Request body must be a JSON object."), 400

    # Never trust the client: validate again on the server.
    errors = validate_purchase(data)
    if errors:
        return jsonify(success=False, message="Validation failed.", errors=errors), 422

    price, _ = parse_price(data["price"])
    record = {
        "order_id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
        "product_id": data["product_id"].strip(),
        "description": data["description"].strip(),
        "customer_name": data["customer_name"].strip(),
        "customer_email": data["customer_email"].strip().lower(),
        "price": str(price),
        "is_online": data["is_online"],
        "channel": "Online" if data["is_online"] else "In store",
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    PURCHASES.append(record)
    return jsonify(success=True, message="Purchase recorded.", purchase=record), 201


@app.get("/api/purchases")
def list_purchases():
    return jsonify(purchases=PURCHASES, count=len(PURCHASES))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
