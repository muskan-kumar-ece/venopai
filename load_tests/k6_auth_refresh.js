import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: __ENV.VUS ? parseInt(__ENV.VUS, 10) : 20,
  duration: __ENV.DURATION || "1m",
};

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
const AUTH_PASSWORD = __ENV.AUTH_PASSWORD || "";
const AUTH_EMAIL = __ENV.AUTH_EMAIL || "";
const AUTH_EMAILS = (__ENV.AUTH_EMAILS || "").split(",").map((item) => item.trim()).filter(Boolean);

let refreshToken = "";

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
  return response.json().refresh;
}

export default function () {
  if (!refreshToken) {
    refreshToken = login();
    if (!refreshToken) {
      sleep(1);
      return;
    }
  }

  const response = http.post(
    `${BASE_URL}/auth/token/refresh/`,
    JSON.stringify({ refresh: refreshToken }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(response, {
    "refresh ok": (res) => res.status === 200 || res.status === 401,
  });

  sleep(1);
}
