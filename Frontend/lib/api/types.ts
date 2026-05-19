export type JwtPair = {
  access: string;
  refresh: string;
};

export type JwtRefreshResponse = {
  access: string;
  refresh?: string;
};

export type Product = {
  id: number;
  category: number;
  category_name: string;
  name: string;
  slug: string;
  description: string;
  price: string;
  sku: string;
  stock_quantity: number;
  is_refurbished: boolean;
  condition_grade: string;
  is_active: boolean;
  average_rating?: number;
  reviews_count?: number;
  image_url?: string | null;
  image_url_card?: string | null;
  image_url_detail?: string | null;
  images?: ProductImage[];
  created_at: string;
  updated_at: string;
};

export type ProductImage = {
  id: number;
  product: number;
  image_url: string;
  image_url_thumbnail?: string;
  image_url_card?: string;
  image_url_detail?: string;
  alt_text?: string;
  is_primary: boolean;
  sort_order: number;
  width?: number | null;
  height?: number | null;
  format?: string;
};

export type Category = {
  id: number;
  name: string;
  slug: string;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type ProductReview = {
  id: number;
  product: number;
  user_name: string;
  rating: number;
  title: string;
  is_mine?: boolean;
  comment: string;
  created_at: string;
  updated_at?: string;
};

export type WishlistItem = {
  id: number;
  product: number;
  product_details?: Product;
  product_name?: string;
  product_price?: string;
  image_url?: string;
  created_at?: string;
  updated_at?: string;
};

/** @deprecated Legacy cart line shape — use ServerCartItem for server-backed cart APIs. */
export type CartItem = {
  id: number;
  cart: number;
  product: number;
  quantity: number;
  created_at: string;
  updated_at: string;
};

/** @deprecated Legacy cart header — use ServerCart for server-backed cart APIs. */
export type Cart = {
  id: number;
  user: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

/** Nested product payload returned on cart line items (`GET /orders/carts/active/`). */
export type CartProductSummary = {
  id: number;
  name: string;
  slug: string;
  sku: string;
  price: string;
  stock_quantity: number;
  is_active: boolean;
  is_refurbished: boolean;
  condition_grade: string;
  category_name: string;
  image_url: string | null;
  image_url_card?: string | null;
};

/** Server-backed cart line with nested product (quantity-based, one row per product). */
export type ServerCartItem = {
  id: number;
  cart: number;
  product: CartProductSummary;
  quantity: number;
  line_total: string;
  created_at: string;
  updated_at: string;
};

/** Server-backed cart header. */
export type ServerCart = {
  id: number;
  user: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

/** React Query–friendly active cart payload from `GET /api/v1/orders/carts/active/`. */
export type ServerCartView = {
  id: number;
  user: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  items: ServerCartItem[];
  item_count: number;
  subtotal: string;
};

export type Order = {
  id: number;
  user: string;
  total_amount: string;
  gross_amount?: string | null;
  coupon_discount?: string;
  applied_coupon?: number | null;
  status: string;
  payment_status: string;
  tracking_id: string | null;
  reservation_expires_at?: string | null;
  reservation_released_at?: string | null;
  shipping_provider?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  shipping_events?: ShippingEvent[];
  items?: OrderItem[];
  created_at: string;
  updated_at: string;
};

export type ShippingEvent = {
  id: number;
  event_type: "created" | "picked_up" | "in_transit" | "out_for_delivery" | "delivered";
  location: string;
  timestamp: string;
};

export type OrderItem = {
  id: number;
  order: number;
  product: number;
  quantity: number;
  price: string;
  created_at: string;
  updated_at: string;
};

export type RazorpayPaymentSession = {
  payment_id: number;
  razorpay_order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  retry_attempt?: number;
};

export type CheckoutFromCartResponse = {
  order: Order;
  payment: RazorpayPaymentSession;
  reservation_expires_at?: string | null;
};

export type AnalyticsSummary = {
  total_revenue: string;
  total_orders: number;
  total_paid_orders: number;
  total_refunded_orders: number;
  refund_rate_percent: number;
  today_revenue: string;
  today_orders: number;
  last_7_days_revenue: string;
};

export type AdminTopProduct = {
  product_id: number;
  name: string;
  total_sold: number;
};

export type AdminRecentOrder = {
  order_id: number;
  user_email: string;
  total_amount: string;
  status: string;
  created_at: string;
};

export type AdminAnalyticsDashboard = {
  total_orders: number;
  total_revenue: string;
  total_users: number;
  top_products: AdminTopProduct[];
  recent_orders: AdminRecentOrder[];
};

export type AdminOrderListItem = {
  id: number;
  user_email: string;
  total_amount: string;
  payment_status: string;
  status: string;
  created_at: string;
};

export type AdminOrderEvent = {
  id: number;
  previous_status: string;
  new_status: string;
  previous_payment_status: string;
  new_payment_status: string;
  note: string;
  changed_by_email?: string;
  changed_by_name?: string;
  created_at: string;
};

export type AdminShippingAddress = {
  full_name: string;
  phone_number: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
};

export type AdminOrderDetail = {
  id: number;
  user: string;
  user_email: string;
  user_name: string;
  total_amount: string;
  gross_amount?: string | null;
  coupon_discount?: string;
  status: string;
  payment_status: string;
  tracking_id: string | null;
  created_at: string;
  updated_at: string;
  items: Array<{
    id: number;
    product: number;
    product_name: string;
    quantity: number;
    price: string;
  }>;
  shipping_address?: AdminShippingAddress | null;
  timeline: AdminOrderEvent[];
};

export type ReferralSummary = {
  referral_code: string;
  total_referrals: number;
  successful_referrals: number;
  pending_rewards: number;
  earned_rewards: string;
  referral_link: string;
  reward_coupon_codes: string[];
};
