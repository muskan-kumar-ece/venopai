"use client";

import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  Headphones,
  PackageCheck,
  RotateCcw,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Star,
  Truck,
  Zap,
} from "lucide-react";

import { type CartProduct, useCart, useCartUI } from "@/components/providers/cart-context";
import { ProductCard, ProductCardSkeleton } from "@/components/products/product-card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const featuredProducts: Array<CartProduct & {
  description: string;
  image: string;
  category_name: string;
  stock_quantity: number;
  average_rating: number;
  reviews_count: number;
  compareAtPrice: string;
  badge: string;
}> = [
  {
    id: 1,
    name: "Aurora Smartwatch",
    price: "Rs. 7,499",
    compareAtPrice: "Rs. 9,999",
    description: "Precision tracking with an elegant titanium finish.",
    category_name: "Smart wearables",
    stock_quantity: 18,
    average_rating: 4.8,
    reviews_count: 214,
    badge: "Best seller",
    image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 2,
    name: "Luma Wireless Earbuds",
    price: "Rs. 4,299",
    compareAtPrice: "Rs. 5,499",
    description: "Immersive sound tuned for all-day comfort and clarity.",
    category_name: "Audio essentials",
    stock_quantity: 27,
    average_rating: 4.7,
    reviews_count: 186,
    badge: "Top rated",
    image: "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 3,
    name: "Nimbus Travel Backpack",
    price: "Rs. 3,899",
    compareAtPrice: "Rs. 4,799",
    description: "Minimal silhouette with premium weather-resistant fabric.",
    category_name: "Travel picks",
    stock_quantity: 9,
    average_rating: 4.6,
    reviews_count: 92,
    badge: "Travel ready",
    image: "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 4,
    name: "Quartz Desk Lamp",
    price: "Rs. 2,199",
    compareAtPrice: "Rs. 2,799",
    description: "Soft ambient lighting with modern touch controls.",
    category_name: "Work setup",
    stock_quantity: 14,
    average_rating: 4.9,
    reviews_count: 73,
    badge: "New arrival",
    image: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=80",
  },
];

const categories = [
  {
    label: "Smart wearables",
    description: "Track, train, and stay connected.",
    href: "/products?q=smartwatch",
    icon: Zap,
    accent: "from-primary-600 to-info-500",
  },
  {
    label: "Audio essentials",
    description: "Earbuds and speakers for daily flow.",
    href: "/products?q=audio",
    icon: Headphones,
    accent: "from-error-500 to-warning-500",
  },
  {
    label: "Work setup",
    description: "Clean tools for focused spaces.",
    href: "/products?q=desk",
    icon: Sparkles,
    accent: "from-success-600 to-primary-500",
  },
  {
    label: "Travel picks",
    description: "Reliable carry for movement.",
    href: "/products?q=travel",
    icon: ShoppingBag,
    accent: "from-surface-800 to-primary-700",
  },
];

const trustItems = [
  {
    title: "Secure checkout",
    description: "Encrypted payments and protected order flow.",
    icon: ShieldCheck,
  },
  {
    title: "Reliable delivery",
    description: "Fast dispatch with clear order visibility.",
    icon: Truck,
  },
  {
    title: "Genuine products",
    description: "Curated catalog with quality-first selection.",
    icon: BadgeCheck,
  },
  {
    title: "Easy returns",
    description: "Simple support when something is not right.",
    icon: RotateCcw,
  },
];

function FeaturedProductsSection({
  onAddProduct,
}: {
  onAddProduct: (product: CartProduct) => void;
}) {
  const products = featuredProducts;

  return (
    <section id="featured-products" aria-labelledby="featured-heading" className="mx-auto w-full max-w-[1280px] px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
      <div className="mb-6 flex flex-col gap-3 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">
            Featured drops
          </p>
          <h2 id="featured-heading" className="mt-2 text-2xl font-bold tracking-tight text-surface-950 dark:text-surface-50 sm:text-3xl">
            Popular picks, ready to ship
          </h2>
        </div>
        <Button asChild variant="outline" className="w-full rounded-full sm:w-auto">
          <Link href="/products">
            View all products <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
          </Link>
        </Button>
      </div>

      {products.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {products.map((product, index) => (
            <ProductCard
              key={product.id}
              product={product}
              href={`/products?q=${encodeURIComponent(product.name)}`}
              onAddToCart={() => onAddProduct(product)}
              priority={index === 0}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-surface-300 bg-white p-8 text-center dark:border-surface-700 dark:bg-surface-900">
          <PackageCheck className="mx-auto h-8 w-8 text-primary-600" aria-hidden="true" />
          <p className="mt-3 text-sm font-medium text-surface-700 dark:text-surface-200">
            Featured products are being refreshed.
          </p>
        </div>
      )}
    </section>
  );
}

function ProductSkeletonGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Loading featured products">
      {Array.from({ length: 4 }).map((_, index) => (
        <ProductCardSkeleton key={index} />
      ))}
    </div>
  );
}

function StorefrontContent() {
  const { openDrawer } = useCartUI();
  const { totalItems, isLoading, addToCart } = useCart();

  const handleAddProduct = (product: CartProduct) => {
    void addToCart(product);
    openDrawer();
  };

  return (
    <div className="bg-gradient-to-b from-primary-50 via-white to-surface-50 dark:from-neutral-950 dark:via-neutral-950 dark:to-surface-900">
      <section className="mx-auto grid min-h-[calc(100vh-9rem)] w-full max-w-[1280px] items-center gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1.02fr_0.98fr] lg:px-8 lg:py-14">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-white/80 px-3 py-1 text-xs font-semibold text-primary-700 shadow-sm backdrop-blur dark:border-primary-900 dark:bg-surface-900/80 dark:text-primary-300">
            <Star className="h-3.5 w-3.5 fill-primary-500 text-primary-500" aria-hidden="true" />
            Premium essentials, curated for modern shopping
          </div>
          <h1 className="mt-5 text-4xl font-black tracking-tight text-surface-950 dark:text-white sm:text-5xl lg:text-6xl">
            Discover products that feel good from click to doorstep.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-surface-600 dark:text-surface-300 sm:text-lg">
            Shop refined everyday tech, travel, and home essentials with secure checkout, reliable delivery, and a cleaner buying experience.
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="rounded-full">
              <Link href="#featured-products">
                Shop featured picks <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button type="button" size="lg" variant="secondary" onClick={openDrawer} className="rounded-full">
              Cart ({totalItems})
            </Button>
          </div>
          <dl className="mt-8 grid grid-cols-3 gap-3 rounded-2xl border border-white/80 bg-white/70 p-3 text-center shadow-sm backdrop-blur dark:border-surface-800 dark:bg-surface-900/70">
            <div>
              <dt className="text-lg font-black text-surface-950 dark:text-white">4.8</dt>
              <dd className="text-xs text-surface-600 dark:text-surface-300">Shopper rating</dd>
            </div>
            <div>
              <dt className="text-lg font-black text-surface-950 dark:text-white">50K+</dt>
              <dd className="text-xs text-surface-600 dark:text-surface-300">Orders served</dd>
            </div>
            <div>
              <dt className="text-lg font-black text-surface-950 dark:text-white">100%</dt>
              <dd className="text-xs text-surface-600 dark:text-surface-300">Secure flow</dd>
            </div>
          </dl>
        </div>

        <div className="relative">
          <div className="absolute inset-4 rounded-[2rem] bg-primary-200/50 blur-3xl dark:bg-primary-900/30" aria-hidden="true" />
          <div className="relative overflow-hidden rounded-[2rem] border border-white/80 bg-white p-3 shadow-2xl shadow-primary-900/15 dark:border-surface-800 dark:bg-surface-900">
            <div className="relative aspect-[4/5] overflow-hidden rounded-[1.5rem] bg-surface-100 sm:aspect-[5/4] lg:aspect-[4/5]">
              <Image
                src="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80"
                alt="Premium devices arranged for online shopping"
                fill
                sizes="(max-width: 1024px) 92vw, 48vw"
                className="object-cover"
                priority
              />
              <div className="absolute inset-x-4 bottom-4 rounded-2xl bg-white/90 p-4 shadow-lg backdrop-blur dark:bg-surface-950/90">
                <p className="text-sm font-semibold text-surface-950 dark:text-white">This week&apos;s curated edit</p>
                <p className="mt-1 text-xs text-surface-600 dark:text-surface-300">
                  Smart devices, audio, and desk upgrades with premium support.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="category-heading" className="mx-auto w-full max-w-[1280px] px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">Browse faster</p>
            <h2 id="category-heading" className="mt-2 text-2xl font-bold tracking-tight text-surface-950 dark:text-white">
              Shop by intent
            </h2>
          </div>
          <Link href="/products" className="hidden text-sm font-semibold text-primary-700 hover:text-primary-800 sm:inline dark:text-primary-300">
            All categories
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <Link
                key={category.label}
                href={category.href}
                className="group rounded-2xl border border-surface-200 bg-white p-4 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary-200 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-surface-800 dark:bg-surface-900"
              >
                <span className={cn("flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-sm", category.accent)}>
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-base font-bold text-surface-950 dark:text-white">{category.label}</h3>
                <p className="mt-1 text-sm text-surface-600 dark:text-surface-300">{category.description}</p>
              </Link>
            );
          })}
        </div>
      </section>

      {isLoading ? (
        <section className="mx-auto w-full max-w-[1280px] px-4 py-12 sm:px-6 lg:px-8">
          <ProductSkeletonGrid />
        </section>
      ) : (
        <FeaturedProductsSection onAddProduct={handleAddProduct} />
      )}

      <section aria-labelledby="trust-heading" className="mx-auto w-full max-w-[1280px] px-4 pb-16 sm:px-6 lg:px-8 lg:pb-20">
        <div className="rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-6">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">Built for confidence</p>
              <h2 id="trust-heading" className="mt-2 text-2xl font-bold tracking-tight text-surface-950 dark:text-white">
                Premium service without the noise
              </h2>
            </div>
            <PackageCheck className="hidden h-8 w-8 text-success-600 sm:block" aria-hidden="true" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {trustItems.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="rounded-2xl bg-surface-50 p-4 dark:bg-surface-800">
                  <Icon className="h-5 w-5 text-primary-600 dark:text-primary-300" aria-hidden="true" />
                  <h3 className="mt-3 text-sm font-bold text-surface-950 dark:text-white">{item.title}</h3>
                  <p className="mt-1 text-sm leading-5 text-surface-600 dark:text-surface-300">{item.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}

export default function ProductListingPage() {
  return <StorefrontContent />;
}
