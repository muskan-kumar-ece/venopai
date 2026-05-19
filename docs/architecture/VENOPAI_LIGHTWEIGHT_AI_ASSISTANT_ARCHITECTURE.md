# Venopai Lightweight AI Assistant Architecture

## 1) Purpose and scope
Venopai Assistant is a **domain assistant**, not a general chatbot.
It should only help with:
- product suggestions from Venopai catalog
- printing option guidance for students
- trending item recommendations from platform analytics
- contextual help inside Venopai flows (product page, cart, checkout)

If a user asks for out-of-scope content, the assistant should politely decline and redirect to supported tasks.

## 2) Lightweight architecture (affordable by default)
Use a two-stage pipeline:

1. **Deterministic context builder (backend service)**
   - Fetches only necessary structured data from existing APIs:
     - products API (`/api/v1/products/...`)
     - cart/orders context (`/api/v1/orders/...`)
     - user profile/role (`/api/v1/users/...`)
     - trending aggregates (precomputed daily/near-real-time table)
   - Applies hard filters (price range, stock, print constraints, user role).
   - Produces compact JSON context.

2. **Small LLM response generator**
   - Receives user intent + compact context JSON + strict instruction prompt.
   - Returns structured output (recommendations + reasons + confidence + fallback).

This keeps token usage low because the model never sees the full catalog.

## 3) Prompt structure
Use fixed prompt sections to make behavior predictable.

### System prompt (static)
- Identity: "You are Venopai Assistant for ecommerce and print guidance."
- Policy: "Use only provided context. Do not invent products, prices, availability, policies, or delivery promises."
- Scope: only Venopai shopping/printing help.
- Output format: strict JSON schema.

### Developer prompt (static)
- Explain ranking priorities:
  1. user suitability (course/use-case)
  2. availability/in-stock
  3. budget fit
  4. trending boost
- Explain refusal behavior when context is missing.
- Enforce max recommendations (e.g., 3).

### User prompt (dynamic)
- Raw user message
- Current page context (product/cart/checkout/admin)
- Optional selected filters (budget, color mode, paper size, turnaround time)

### Context payload (dynamic JSON, server-built)
```json
{
  "session": {"user_id": "uuid", "role": "student", "currency": "INR"},
  "page": {"name": "checkout", "cart_total": 540},
  "intent": {"type": "print_options"},
  "catalog_candidates": [
    {
      "id": 12,
      "name": "A4 Color Notes Print",
      "price": 3.5,
      "stock": true,
      "tags": ["notes", "student", "color"]
    }
  ],
  "trending": [{"product_id": 12, "score": 0.92}],
  "constraints": {"max_budget": 600, "delivery_deadline": "2026-03-05"}
}
```

## 4) Context contract: what to pass (and what not to pass)
Pass:
- only top-k candidate products (e.g., 20 max)
- pricing, stock, lead time, print capabilities, ratings summary
- user-relevant history signals (recently viewed/category affinity), not raw event logs
- trending summary scores, not full analytics tables

Avoid passing:
- full catalog dumps
- sensitive PII beyond minimal identifiers
- unverifiable marketing claims

## 5) Hallucination prevention strategy
1. **Grounding-first**: model answers only from `catalog_candidates`, `trending`, and `constraints`.
2. **Structured output schema** (validated server-side):
   - `answer`
   - `recommended_product_ids[]`
   - `reasons[]`
   - `missing_data[]`
   - `confidence` (0-1)
3. **Server validator** rejects unknown product IDs or invalid price references.
4. **Fallback response** when confidence is low or context missing:
   - "I need one more detail: print type / budget / delivery timeline."
5. **No free-form policy claims** unless present in context.

## 6) Recommendation logic (hybrid)
Use deterministic ranking before LLM narrative:

`final_score = 0.45 * relevance + 0.25 * budget_fit + 0.20 * trending + 0.10 * margin_or_stock_health`

- Backend computes final ranked items.
- LLM only explains top picks in human language.
- This gives consistency and lower hallucination risk.

## 7) Runtime integration in Venopai
- Frontend (Next.js) sends lightweight request to `/api/v1/assistant/respond/`.
- Backend assembles context and calls LLM provider.
- Response includes recommendation cards + explanation + follow-up question.
- UI shows assistant only in storefront/student flows (not a global chat app).

## 8) Cost controls
- Use a **small model** for most requests.
- Limit tokens with compact context + strict output schema.
- Cache frequent intents (e.g., "best print option under INR 500").
- Reuse trending context snapshots for a time window.
- Add request budget guardrails per user/session.

## 9) Observability and quality loop
Track:
- suggestion CTR
- add-to-cart conversion after assistant suggestion
- checkout completion uplift
- clarification rate (how often assistant asks follow-up)
- invalid response rate from schema validator

Use offline evaluation sets from real anonymized queries to tune ranking weights and prompt wording.

## 10) Non-goal reminder
Venopai Assistant should remain **small contextual intelligence** for commerce + printing decisions.
It should not attempt open-domain Q&A, coding help, or general-purpose conversation.
