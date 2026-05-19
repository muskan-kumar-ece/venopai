# Cart Migration Consolidation

## Scope
This document consolidates the backend and frontend cart migration notes for May 2026.

## Summary
- Server cart is the source of truth for authenticated users.
- A single active cart endpoint returns nested product summaries.
- Frontend cart state is moving to React Query; UI drawer state remains local.

## Backend Changes
New logic:
- Active cart lookup and helpers (orders/cart_services.py).
- Active cart endpoint and clear action.
- Cart item create now merges quantity on duplicate product.

Endpoints:
- GET /api/v1/orders/carts/active/ : Active cart with items, counts, and subtotal.
- DELETE /api/v1/orders/carts/active/clear/ : Clear active cart items.

Behavior changes:
- Cart item reads include nested product details and line totals.
- Server prefetch joins product, category, images.

## Frontend Changes
- React Query is the data source for cart state.
- New cart domain utilities, query hooks, and optimistic updates.
- Cart drawer UI is now separate from cart data.

## Current Status (Not Migrated Yet)
- Checkout page still uses legacy adapter (client cart expansion).
- /cart page still uses legacy fetch adapter.
- Guest cart flow not yet implemented.

## Rollout Checklist
1. Deploy backend updates first.
2. Verify active cart endpoint in staging.
3. Migrate /cart and checkout to use useCart() data.
4. Remove legacy adapters after UI migration.
