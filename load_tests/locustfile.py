import os
from locust import HttpUser, between, task


class ShopperUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.email = os.getenv("AUTH_EMAIL", "")
        self.password = os.getenv("AUTH_PASSWORD", "")
        self.product_id = os.getenv("PRODUCT_ID", "")
        self.access = ""
        self.refresh = ""
        self._login()

    def _login(self):
        if not self.email or not self.password:
            return
        response = self.client.post(
            "/api/v1/auth/token/",
            json={"email": self.email, "password": self.password},
        )
        if response.status_code == 200:
            payload = response.json()
            self.access = payload.get("access", "")
            self.refresh = payload.get("refresh", "")

    def _headers(self):
        if not self.access:
            return {}
        return {"Authorization": f"Bearer {self.access}"}

    def _ensure_product_id(self):
        if self.product_id:
            return self.product_id
        response = self.client.get("/api/v1/products/", headers=self._headers())
        if response.status_code != 200:
            return ""
        payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("results", [])
        if not items:
            return ""
        self.product_id = str(items[0].get("id"))
        return self.product_id

    @task(2)
    def browse_catalog(self):
        self.client.get("/api/v1/products/", headers=self._headers())

    @task(1)
    def checkout_from_cart(self):
        if not self.access:
            self._login()
        product_id = self._ensure_product_id()
        if not product_id:
            return
        cart = self.client.get("/api/v1/orders/carts/active/", headers=self._headers())
        if cart.status_code != 200:
            return
        cart_id = cart.json().get("id")
        if not cart_id:
            return
        self.client.post(
            "/api/v1/orders/cart-items/",
            json={"cart": cart_id, "product": int(product_id), "quantity": 1},
            headers=self._headers(),
        )
        self.client.post(
            "/api/v1/orders/checkout-from-cart/",
            json={},
            headers={**self._headers(), "Idempotency-Key": f"locust-{id(self)}"},
        )

    @task(1)
    def refresh_token(self):
        if not self.refresh:
            return
        self.client.post(
            "/api/v1/auth/token/refresh/",
            json={"refresh": self.refresh},
        )
