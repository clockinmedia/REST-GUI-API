# Purchase Entry — Tkinter client + Flask API

A desktop form collects a purchase, checks it on the client, packs it into JSON,
POSTs it to a Flask API and shows the server's reply in the window.

```
client.py  (Tkinter) ──validate──► JSON ──HTTP POST──► server.py (Flask) ──validate again──► 201 / 422
                ▲                                                     │
                └────────────── JSON response shown in the GUI ◄──────┘
```

## Files
| File | Purpose |
|---|---|
| `validation.py` | Validation rules for the client and the server: email format, price > $0 and ≤ $1,000.00 with at most 2 decimals, required fields |
| `client.py` | Tkinter form: entry fields, Online/In-store checkbox, error messages next to each field, POST on a background thread |
| `server.py` | Flask API: `POST /api/purchases`, `GET /api/purchases`, `GET /api/health` |
| `test_app.py` | 31 pytest tests for the validation rules and the API |

## Run
```bash
pip install -r requirements.txt     # tkinter ships with Python (on Linux: apt install python3-tk)
python server.py                    # terminal 1 → http://127.0.0.1:5000
python client.py                    # terminal 2
python -m pytest -q                 # tests
```

## JSON contract
Request sent by the client:
```json
{"product_id": "SKU-1001", "description": "Wireless mouse",
 "customer_name": "Ada Lovelace", "customer_email": "ada@example.com",
 "price": "49.99", "is_online": true}
```
`price` is sent as a 2-decimal string and parsed with `Decimal`, so there is no float rounding.

Responses:
* **201**: `{"success": true, "message": "...", "purchase": {..., "order_id": "ORD-…", "channel": "Online"}}`
* **422**: `{"success": false, "message": "Validation failed.", "errors": {"price": "..."}}`
* **400**: the body is not a JSON object

## How it maps to the learning objectives
* **Form design.** Labels mark required fields with `*`. Each error appears under its field and the field turns red. The email and price fields are checked as you type or leave them. Enter submits the form, Clear resets it, and Submit is disabled while a request is in flight.
* **Client-side validation.** `validate_purchase()` runs before any network call. The first invalid field gets focus.
* **JSON + HTTP POST.** The form uses `json.dumps` and `requests.post` with `Content-Type: application/json` and a 10 s timeout.
* **Consuming responses.** The status line and a message box report success or failure. The raw JSON appears in the response pane. Server-side field errors (422) are mapped back to the matching fields. Connection errors and timeouts get clear messages.
* **Thread safety.** The POST runs on a worker thread, and the result returns to Tk through `after(0, …)`, so the window never freezes.
