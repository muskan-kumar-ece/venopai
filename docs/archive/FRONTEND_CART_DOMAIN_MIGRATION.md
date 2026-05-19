# Frontend Cart Domain Migration

**Scope:** React Query as cart source of truth; `CartContext` is UI-only. Checkout and Razorpay unchanged.

---

## New files

| File | Role |
|------|------|
| `Frontend/lib/cart/cart-utils.ts` | Parsing, rollups, legacy checkout line expansion, optimistic helpers |
| `Frontend/lib/cart/cart-query.ts` | `cartQueryKeys`, query options, mutations + optimistic updates |
| `Frontend/lib/cart/use-cart.ts` | `useCart()` public domain hook |
| `Frontend/lib/cart/index.ts` | Barrel exports |

## Modified files

| File | Change |
|------|--------|
| `Frontend/components/providers/cart-context.tsx` | Drawer UI only (`useCartUI`); re-exports `useCart` |
| `Frontend/components/layout/cart-drawer.tsx` | Server cart + `useCartUI` (no props) |
| `Frontend/app/(store)/page.tsx` | Removed nested `CartProvider`; drawer via `useCartUI` |

## Architecture

```
CartProvider (UI)
  └── isDrawerOpen, openDrawer, closeDrawer

useCart() (data)
  └── React Query cache ← cartQueryKeys.active()
        └── GET /api/v1/orders/carts/active/
  └── mutations → invalidate / setQueryData
```

## `useCart()` API

| Member | Description |
|--------|-------------|
| `cart` | Server cart header or `null` |
| `items` | `ServerCartItem[]` with nested `product` |
| `subtotal` / `subtotalAmount` | Server rollups |
| `itemCount` | Sum of line quantities |
| `addToCart` | By `productId` or legacy `CartProductInput` |
| `updateQuantity` | PATCH line quantity |
| `removeItem` | DELETE line |
| `clearCart` | DELETE active/clear |
| `refetch` | React Query refetch |
| `cartItems` / `totalPrice` / `totalItems` | Legacy checkout adapters |

## React Query

```typescript
import { cartQueryKeys } from "@/lib/cart";

useQuery({ queryKey: cartQueryKeys.active(), queryFn: getCart, enabled: isAuthenticated });
```

Mutations optimistically update cache when authenticated; always `invalidateQueries` on settle.

## Next PR (not done)

- Migrate `checkout/page.tsx` to `items` + quantities (drop `cartItems` expansion)
- Migrate `/cart` page to `useCart()` instead of `fetchCart`
- Guest cart: separate query key + `enabled` when anonymous
- Coupons: extend `ServerCartView` with `discount` / `total` fields
