"""Tkinter desktop form that validates a purchase and POSTs it as JSON to the Flask API.

Run the server first (python server.py), then:  python client.py
Optional: python client.py --url http://host:port/api/purchases
"""
import argparse
import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import requests

from validation import parse_price, validate_email, validate_purchase

DEFAULT_URL = "http://127.0.0.1:5000/api/purchases"
ERROR_COLOR = "#b00020"
OK_COLOR = "#1b6e20"


class PurchaseForm(ttk.Frame):
    FIELDS = [
        ("product_id", "Product ID"),
        ("description", "Description"),
        ("customer_name", "Customer Name"),
        ("customer_email", "Customer Email"),
        ("price", "Price (USD)"),
    ]

    def __init__(self, master: tk.Tk, api_url: str):
        super().__init__(master, padding=16)
        self.api_url = api_url
        self.vars: dict[str, tk.StringVar] = {}
        self.entries: dict[str, ttk.Entry] = {}
        self.error_labels: dict[str, ttk.Label] = {}
        self.is_online = tk.BooleanVar(value=True)
        self._build()

    # ---------- layout ----------
    def _build(self):
        style = ttk.Style(self)
        style.configure("Error.TLabel", foreground=ERROR_COLOR, font=("TkDefaultFont", 8))
        style.configure("Header.TLabel", font=("TkDefaultFont", 13, "bold"))
        style.configure("Invalid.TEntry", fieldbackground="#fdecea")

        ttk.Label(self, text="New Purchase", style="Header.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        row = 1
        for key, label in self.FIELDS:
            ttk.Label(self, text=label + " *").grid(row=row, column=0, sticky="w", padx=(0, 10))
            var = tk.StringVar()
            entry = ttk.Entry(self, textvariable=var, width=38)
            entry.grid(row=row, column=1, sticky="ew")
            err = ttk.Label(self, text="", style="Error.TLabel")
            err.grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
            self.vars[key], self.entries[key], self.error_labels[key] = var, entry, err
            row += 2

        # Live validation for the two rules the assignment calls out.
        self.entries["customer_email"].bind("<FocusOut>", lambda e: self._check_field("customer_email"))
        self.entries["price"].bind("<FocusOut>", lambda e: self._check_field("price"))
        self.entries["price"].bind("<KeyRelease>", lambda e: self._check_field("price"))

        ttk.Checkbutton(self, text="Online purchase (uncheck for in-store)",
                        variable=self.is_online).grid(row=row, column=1, sticky="w", pady=(2, 10))
        row += 1

        buttons = ttk.Frame(self)
        buttons.grid(row=row, column=1, sticky="e")
        ttk.Button(buttons, text="Clear", command=self.clear).pack(side="left", padx=(0, 8))
        self.submit_btn = ttk.Button(buttons, text="Submit", command=self.submit)
        self.submit_btn.pack(side="left")
        row += 1

        ttk.Separator(self).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        self.status = ttk.Label(self, text=f"API: {self.api_url}", wraplength=420)
        self.status.grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        ttk.Label(self, text="Server response:").grid(row=row, column=0, sticky="nw", pady=(8, 0))
        self.response_box = tk.Text(self, height=9, width=50, state="disabled",
                                    font=("TkFixedFont", 9), relief="solid", borderwidth=1)
        self.response_box.grid(row=row, column=1, sticky="ew", pady=(8, 0))

        self.columnconfigure(1, weight=1)
        self.master.bind("<Return>", lambda e: self.submit())
        self.entries["product_id"].focus_set()

    # ---------- validation helpers ----------
    def _set_error(self, key: str, message: str | None):
        self.error_labels[key].configure(text=message or "")
        self.entries[key].configure(style="Invalid.TEntry" if message else "TEntry")

    def _check_field(self, key: str):
        value = self.vars[key].get()
        if key == "customer_email":
            self._set_error(key, validate_email(value) if value.strip() else None)
        elif key == "price":
            self._set_error(key, parse_price(value)[1] if value.strip() else None)

    def collect(self) -> dict:
        return {
            "product_id": self.vars["product_id"].get().strip(),
            "description": self.vars["description"].get().strip(),
            "customer_name": self.vars["customer_name"].get().strip(),
            "customer_email": self.vars["customer_email"].get().strip(),
            "price": self.vars["price"].get().strip(),
            "is_online": self.is_online.get(),
        }

    # ---------- actions ----------
    def submit(self):
        data = self.collect()
        errors = validate_purchase(data)
        for key, _ in self.FIELDS:
            self._set_error(key, errors.get(key))
        if errors:
            self._set_status(f"Please fix {len(errors)} field(s) before submitting.", ERROR_COLOR)
            self.entries[next(k for k, _ in self.FIELDS if k in errors)].focus_set()
            return

        # Normalise price to a 2-decimal string so the JSON is exact (no float rounding).
        data["price"] = str(parse_price(data["price"])[0])
        payload = json.dumps(data)

        self.submit_btn.configure(state="disabled")
        self._set_status("Sending…", "black")
        # Network call on a worker thread keeps the window responsive.
        threading.Thread(target=self._post, args=(payload,), daemon=True).start()

    def _post(self, payload: str):
        try:
            resp = requests.post(self.api_url, data=payload, timeout=10,
                                 headers={"Content-Type": "application/json"})
            try:
                body = resp.json()
            except ValueError:
                body = {"message": resp.text[:300]}
            result = (resp.status_code, body, None)
        except requests.ConnectionError:
            result = (None, None, "Could not connect to the API. Is server.py running?")
        except requests.Timeout:
            result = (None, None, "The API did not respond in time.")
        except requests.RequestException as exc:
            result = (None, None, f"Request failed: {exc}")
        # Tkinter is not thread-safe: hand the result back to the main loop.
        self.after(0, self._handle_response, *result)

    def _handle_response(self, status, body, network_error):
        self.submit_btn.configure(state="normal")
        if network_error:
            self._set_status(network_error, ERROR_COLOR)
            messagebox.showerror("Connection error", network_error)
            return

        self._show_json(body)
        if status == 201 and body.get("success"):
            order = body["purchase"]
            msg = f"✔ {body['message']} Order {order['order_id']} — ${order['price']} ({order['channel']})"
            self._set_status(msg, OK_COLOR)
            messagebox.showinfo("Success", msg)
            self.clear(keep_status=True)
        else:
            for key, err in (body.get("errors") or {}).items():
                if key in self.entries:
                    self._set_error(key, err)
            self._set_status(f"Server rejected the request (HTTP {status}): "
                             f"{body.get('message', 'Unknown error')}", ERROR_COLOR)

    def clear(self, keep_status: bool = False):
        for key, _ in self.FIELDS:
            self.vars[key].set("")
            self._set_error(key, None)
        self.is_online.set(True)
        if not keep_status:
            self._set_status(f"API: {self.api_url}", "black")
            self._show_json(None)
        self.entries["product_id"].focus_set()

    def _set_status(self, text: str, color: str):
        self.status.configure(text=text, foreground=color)

    def _show_json(self, body):
        self.response_box.configure(state="normal")
        self.response_box.delete("1.0", "end")
        if body is not None:
            self.response_box.insert("1.0", json.dumps(body, indent=2))
        self.response_box.configure(state="disabled")


def main():
    parser = argparse.ArgumentParser(description="Purchase entry desktop client")
    parser.add_argument("--url", default=DEFAULT_URL, help="Purchases API endpoint")
    args = parser.parse_args()

    root = tk.Tk()
    root.title("Purchase Entry")
    root.resizable(False, False)
    PurchaseForm(root, args.url).pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
