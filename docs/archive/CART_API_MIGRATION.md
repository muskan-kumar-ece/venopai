# Cart API Migration Notes

**Date:** May 2026  
**Scope:** Server cart as single source of truth — API/sync layer only (checkout and UI unchanged).

---

## Summary

The cart stack now exposes a **single round-trip active cart** endpoint with **nested product summaries**, and the frontend `lib/api/cart.ts` module is a full **service layer** for React Query consumers.

---

## Backend changes

### New files

| File | Purpose |
|------|---------|
| `Backend/orders/cart_services.py` | Active cart lookup, prefetch, clear helpers |

### Modified files

| File | Changes |
|------|---------|
| `Backend/orders/serializers.py` | `CartProductSummarySerializer`, `CartItemReadSerializer`, `CartItemWriteSerializer`, `ServerCartViewSerializer` |
| `Backend/orders/views.py` | `CartViewSet.active`, `CartViewSet.clear_active`, `CartItemViewSet` read/write serializers + quantity merge on create |

### New endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/v1/orders/carts/active/` | Active cart + nested items + `item_count` + `subtotal` (creates empty cart if missing) |
| `DELETE` | `/api/v1/orders/carts/active/clear/` | Removes all line items from active cart |

### Changed behavior

| Area | Before | After |
|------|--------|-------|
| `GET /cart-items/` | Flat `product` id only | Nested `product` object + `line_total` |
| `POST /cart-items/` | Duplicate product → DB error | **Upsert:** increments `quantity` on existing line |
| Product join | Client fetched all products | Server prefetches `product`, `category`, `images` |

### Unchanged constraints

- `unique_active_cart_per_user` — still one `is_active=True` cart per user
- `unique_product_per_cart` — still one row per product; quantity on row

---

## Frontend changes

### Modified files

| File | Changes |
|------|---------|
| `Frontend/lib/api/cart.ts` | Full service: `ensureActiveCart`, `getCart`, `addToCart`, `updateCartItem`, `removeCartItem`, `clearCart`, `cartQueryKeys` |
| `Frontend/lib/api/types.ts` | `CartProductSummary`, `ServerCartItem`, `ServerCart`, `ServerCartView` |

### Legacy compatibility

- `fetchCart()` remains as a **thin adapter** over `getCart()` for `/cart` page until UI migration.
- Old `Cart` / `CartItem` types marked `@deprecated`.

---

## React Query usage (next PR)

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  cartQueryKeys,
  getCart,
  addToCart,
  updateCartItem,
  removeCartItem,
  clearCart,
} from "@/lib/api/cart";

const queryClient = useQueryClient();

const { data, isLoading } = useQuery({
  queryKey: cartQueryKeys.active(),
  queryFn: getCart,
});

const addMutation = useMutation({
  mutationFn: ({ productId, quantity }: { productId: number; quantity?: number }) =>
    addToCart(productId, quantity),
  onSuccess: (cartView) => {
    queryClient.setQueryData(cartQueryKeys.active(), cartView);
  },
});
```

---

## Not migrated yet (intentional)

| Area | Status |
|------|--------|
| `components/providers/cart-context.tsx` | Still local-only |
| `checkout/page.tsx` | Still uses client context |
| `page.tsx` nested `CartProvider` | Unchanged |
| `CreateOrderSerializer` | Does not read server cart |

---

## Rollout checklist

1. Deploy backend first (read serializers are backward compatible for list shape extension).
2. Verify `GET /api/v1/orders/carts/active/` in staging.
3. Switch UI to `cartQueryKeys.active()` + mutations (separate PR).
4. Remove `fetchCart` adapter after `/cart` page uses `ServerCartView` directly.
5. Remove client `CartProvider` after checkout uses server cart.

---

## API response example

`GET /api/v1/orders/carts/active/`

```json
{
  "id": 1,
  "user": "uuid",
  "is_active": true,
  "created_at": "...",
  "updated_at": "...",
  "item_count": 2,
  "subtotal": "2998.00",
  "items": [
    {
      "id": 10,
      "cart": 1,
      "quantity": 2,
      "line_total": "2998.00",
      "product": {
        "id": 5,
        "name": "Arduino Kit",
        "slug": "arduino-kit",
        "sku": "ARD-001",
        "price": "1499.00",
        "stock_quantity": 25,
        "is_active": true,
        "category_name": "Components",
        "image_url": null
      }
    }
  ]
}
```
