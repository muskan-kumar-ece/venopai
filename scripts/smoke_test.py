import json
import os
import sys
import uuid
from urllib import request, error


BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
EMAIL = os.getenv("SMOKE_EMAIL", "")
PASSWORD = os.getenv("SMOKE_PASSWORD", "")
TIMEOUT = int(os.getenv("SMOKE_TIMEOUT", "10"))


def _request(method, path, payload=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8")
            return response.status, _parse_json(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, _parse_json(body)


def _parse_json(body):
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def fail(message):
    print(f"[FAIL] {message}")
    sys.exit(1)


def main():
    print("[SMOKE] Starting smoke test")

    status, _ = _request("GET", "/health/")
    if status != 200:
        fail("health endpoint failed")

    status, _ = _request("GET", "/health/startup/")
    if status != 200:
        fail("startup readiness failed")

    if not EMAIL or not PASSWORD:
        fail("SMOKE_EMAIL and SMOKE_PASSWORD must be set")

    status, login_payload = _request("POST", "/auth/token/", {"email": EMAIL, "password": PASSWORD})
    if status != 200:
        fail("login failed")

    access = login_payload.get("access")
    refresh = login_payload.get("refresh")
    if not access or not refresh:
        fail("missing access or refresh token")

    status, products_payload = _request("GET", "/products/", token=access)
    if status != 200:
        fail("products endpoint failed")

    product_items = []
    if isinstance(products_payload, list):
        product_items = products_payload
    elif isinstance(products_payload, dict):
        product_items = products_payload.get("results", [])

    status, cart_payload = _request("GET", "/orders/carts/active/", token=access)
    if status != 200:
        fail("active cart endpoint failed")

    cart_id = cart_payload.get("id") if isinstance(cart_payload, dict) else None
    if not cart_id:
        fail("cart id missing")

    if product_items:
        product_id = product_items[0].get("id")
        if product_id:
            status, _ = _request(
                "POST",
                "/orders/cart-items/",
                {"cart": cart_id, "product": product_id, "quantity": 1},
                token=access,
            )
            if status not in {200, 201}:
                fail("add to cart failed")

            idempotency_key = f"smoke-{uuid.uuid4().hex}"
            status, checkout_payload = _request(
                "POST",
                "/orders/checkout-from-cart/",
                {"idempotency_key": idempotency_key},
                token=access,
            )
            if status not in {200, 201}:
                fail("checkout from cart failed")

            _ = checkout_payload

    status, refresh_payload = _request("POST", "/auth/token/refresh/", {"refresh": refresh})
    if status != 200:
        fail("refresh token failed")
    if not isinstance(refresh_payload, dict) or "access" not in refresh_payload:
        fail("refresh token response missing access")

    print("[SMOKE] All checks passed")


if __name__ == "__main__":
    main()
