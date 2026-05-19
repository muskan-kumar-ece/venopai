import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: __ENV.VUS ? parseInt(__ENV.VUS, 10) : 10,
  duration: __ENV.DURATION || "1m",
};

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
const AUTH_PASSWORD = __ENV.AUTH_PASSWORD || "";
const AUTH_EMAIL = __ENV.AUTH_EMAIL || "";
const AUTH_EMAILS = (__ENV.AUTH_EMAILS || "").split(",").map((item) => item.trim()).filter(Boolean);
const PRODUCT_ID = __ENV.PRODUCT_ID || "";

let token = "";
let refreshToken = "";
let cachedProductId = "";

function pickEmail() {
  if (AUTH_EMAILS.length) {
    return AUTH_EMAILS[(__VU - 1) % AUTH_EMAILS.length];
  }
  return AUTH_EMAIL;
}

function login() {
  const email = pickEmail();
  if (!email || !AUTH_PASSWORD) {
    return null;
  }
  const response = http.post(
    `${BASE_URL}/auth/token/`,
    JSON.stringify({ email, password: AUTH_PASSWORD }),
    { headers: { "Content-Type": "application/json" } }
  );
  if (!check(response, { "login ok": (res) => res.status === 200 })) {
    return null;
  }
  const payload = response.json();
  return { access: payload.access, refresh: payload.refresh };
}

function getAuthHeaders() {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

function pickProductId() {
  if (PRODUCT_ID) {
    return PRODUCT_ID;
  }
  if (cachedProductId) {
    return cachedProductId;
  }
  const response = http.get(`${BASE_URL}/products/`, { headers: getAuthHeaders() });
  if (response.status !== 200) {
    return "";
  }
  const payload = response.json();
  const items = Array.isArray(payload) ? payload : payload.results || [];
  if (!items.length) {
    return "";
  }
  cachedProductId = items[0].id;
  return cachedProductId;
}

function ensureActiveCart() {
  const response = http.get(`${BASE_URL}/orders/carts/active/`, { headers: getAuthHeaders() });
  if (response.status !== 200) {
    return null;
  }
  return response.json();
}

export default function () {
  if (!token) {
    const session = login();
    if (!session) {
      sleep(1);
      return;
    }
    token = session.access;
    refreshToken = session.refresh;
  }

  const productId = pickProductId();
  if (!productId) {
    sleep(1);
    return;
  }

  const cart = ensureActiveCart();
  if (!cart) {
    sleep(1);
    return;
  }

  http.post(
    `${BASE_URL}/orders/cart-items/`,
    JSON.stringify({ cart: cart.id, product: productId, quantity: 1 }),
    { headers: getAuthHeaders() }
  );

  const idempotencyKey = `k6-${__VU}-${__ITER}-${Date.now()}`;
  const checkout = http.post(
    `${BASE_URL}/orders/checkout-from-cart/`,
    JSON.stringify({}),
    { headers: { ...getAuthHeaders(), "Idempotency-Key": idempotencyKey } }
  );

  check(checkout, {
    "checkout created or resumed": (res) => res.status === 201 || res.status === 200,
  });

  if (refreshToken && __ITER % 10 === 0) {
    http.post(
      `${BASE_URL}/auth/token/refresh/`,
      JSON.stringify({ refresh: refreshToken }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  sleep(1);
}
