import http from "k6/http";
import { check } from "k6";
import { hmac } from "k6/crypto";

export const options = {
  vus: __ENV.VUS ? parseInt(__ENV.VUS, 10) : 30,
  duration: __ENV.DURATION || "1m",
};

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
const WEBHOOK_SECRET = __ENV.RAZORPAY_WEBHOOK_SECRET || "";
const RAZORPAY_ORDER_ID = __ENV.RAZORPAY_ORDER_ID || "order_stub";

function buildPayload() {
  return {
    event: "payment.failed",
    payload: {
      payment: {
        entity: {
          id: `pay_${__VU}_${__ITER}`,
          order_id: RAZORPAY_ORDER_ID,
        },
      },
    },
  };
}

export default function () {
  const payload = buildPayload();
  const body = JSON.stringify(payload);
  const signature = WEBHOOK_SECRET ? hmac("sha256", WEBHOOK_SECRET, body, "hex") : "";
  const eventId = `evt_${__VU}_${__ITER}_${Date.now()}`;

  const response = http.post(`${BASE_URL}/payments/webhook/`, body, {
    headers: {
      "Content-Type": "application/json",
      "X-Razorpay-Signature": signature,
      "X-Razorpay-Event-Id": eventId,
    },
  });

  check(response, {
    "webhook accepted": (res) => res.status === 200 || res.status === 400,
  });
}
