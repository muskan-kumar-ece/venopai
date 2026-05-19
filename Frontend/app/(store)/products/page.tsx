"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  PackageSearch,
  RotateCcw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Truck,
  X,
} from "lucide-react";

import { useCartUI } from "@/components/providers/cart-context";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { LoadingSkeleton } from "@/components/feedback/loading-skeleton";
import { ProductCard, ProductCardSkeleton } from "@/components/products/product-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetClose, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { fetchProductListing } from "@/lib/api/products";
import type { Product } from "@/lib/api/types";
import { parseDecimal } from "@/lib/cart/cart-utils";
import { useCart } from "@/lib/cart/use-cart";
import { cn } from "@/lib/utils";

const SEARCH_DEBOUNCE_MS = 300;

const categorySuggestions = [
  "electronics",
  "audio",
  "smartwatch",
  "desk",
  "travel",
];

const sortOptions = [
  { value: "featured", label: "Featured" },
  { value: "price-asc", label: "Price: Low to high" },
  { value: "price-desc", label: "Price: High to low" },
  { value: "rating-desc", label: "Top rated" },
  { value: "newest", label: "Newest" },
] as const;

type SortValue = (typeof sortOptions)[number]["value"];

type FilterPanelProps = {
  searchInput: string;
  setSearchInput: (value: string) => void;
  category: string;
  setCategory: (value: string) => void;
  minPriceInput: string;
  setMinPriceInput: (value: string) => void;
  maxPriceInput: string;
  setMaxPriceInput: (value: string) => void;
  inStockOnly: boolean;
  setInStockOnly: (value: boolean) => void;
  resetFilters: () => void;
  activeFilterCount: number;
};

function sortProducts(products: Product[], sort: SortValue) {
  const sorted = [...products];

  switch (sort) {
    case "price-asc":
      return sorted.sort((a, b) => parseDecimal(a.price) - parseDecimal(b.price));
    case "price-desc":
      return sorted.sort((a, b) => parseDecimal(b.price) - parseDecimal(a.price));
    case "rating-desc":
      return sorted.sort((a, b) => (b.average_rating ?? 0) - (a.average_rating ?? 0));
    case "newest":
      return sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    default:
      return sorted;
  }
}

function FilterPanel({
  searchInput,
  setSearchInput,
  category,
  setCategory,
  minPriceInput,
  setMinPriceInput,
  maxPriceInput,
  setMaxPriceInput,
  inStockOnly,
  setInStockOnly,
  resetFilters,
  activeFilterCount,
}: FilterPanelProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-surface-950 dark:text-white">Filters</h2>
          <p className="text-xs text-surface-500 dark:text-surface-400">Refine your product discovery</p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={resetFilters} disabled={activeFilterCount === 0}>
          Reset
        </Button>
      </div>

      <div className="space-y-2">
        <label htmlFor="product-search" className="text-sm font-semibold text-surface-800 dark:text-surface-100">
          Search products
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" aria-hidden="true" />
          <Input
            id="product-search"
            placeholder="Search by name..."
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      <div className="space-y-3">
        <label htmlFor="product-category" className="text-sm font-semibold text-surface-800 dark:text-surface-100">
          Category
        </label>
        <Input
          id="product-category"
          placeholder="e.g. electronics"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {categorySuggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setCategory(suggestion)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
                category === suggestion
                  ? "border-primary-600 bg-primary-600 text-white"
                  : "border-surface-200 bg-white text-surface-700 hover:border-primary-200 hover:bg-primary-50 hover:text-primary-700 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-200 dark:hover:bg-primary-900/30",
              )}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      <fieldset className="space-y-3">
        <legend className="text-sm font-semibold text-surface-800 dark:text-surface-100">Price range</legend>
        <div className="grid grid-cols-2 gap-2">
          <Input
            aria-label="Minimum price"
            type="number"
            min={0}
            placeholder="Min"
            value={minPriceInput}
            onChange={(event) => setMinPriceInput(event.target.value)}
          />
          <Input
            aria-label="Maximum price"
            type="number"
            min={0}
            placeholder="Max"
            value={maxPriceInput}
            onChange={(event) => setMaxPriceInput(event.target.value)}
          />
        </div>
      </fieldset>

      <label className="flex min-h-12 cursor-pointer items-center justify-between gap-3 rounded-2xl border border-surface-200 bg-surface-50 px-3 text-sm font-semibold text-surface-800 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100">
        <span>In stock only</span>
        <input
          type="checkbox"
          checked={inStockOnly}
          onChange={(event) => setInStockOnly(event.target.checked)}
          className="h-5 w-5 accent-primary-600"
        />
      </label>

      <div className="rounded-2xl border border-success-100 bg-success-50 p-4 text-sm text-success-800 dark:border-success-900/40 dark:bg-success-900/20 dark:text-success-300">
        <div className="flex items-center gap-2 font-bold">
          <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          Buyer confidence
        </div>
        <p className="mt-1 text-xs leading-5">Use stock and price filters to find ready-to-ship products with secure checkout.</p>
      </div>
    </div>
  );
}

function ActiveFilterChips({
  filters,
  onRemove,
  onClear,
}: {
  filters: Array<{ key: string; label: string }>;
  onRemove: (key: string) => void;
  onClear: () => void;
}) {
  if (filters.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Active filters">
      {filters.map((filter) => (
        <button
          key={filter.key}
          type="button"
          onClick={() => onRemove(filter.key)}
          className="inline-flex items-center gap-1 rounded-full border border-primary-200 bg-primary-50 px-3 py-1.5 text-xs font-semibold text-primary-800 transition-colors hover:bg-primary-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-primary-900 dark:bg-primary-900/30 dark:text-primary-200"
        >
          {filter.label}
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      ))}
      <Button type="button" variant="ghost" size="sm" onClick={onClear}>
        Clear all
      </Button>
    </div>
  );
}

function ProductsContent() {
  const { openDrawer } = useCartUI();
  const { addToCart, isMutating } = useCart();
  const searchParams = useSearchParams();
  const querySearch = searchParams.get("q") ?? "";
  const [searchInput, setSearchInput] = useState(querySearch);
  const [search, setSearch] = useState("");
  const [category, setCategoryState] = useState("");
  const [minPriceInput, setMinPriceInputState] = useState("");
  const [maxPriceInput, setMaxPriceInputState] = useState("");
  const [inStockOnly, setInStockOnlyState] = useState(false);
  const [sort, setSort] = useState<SortValue>("featured");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setSearchInput(querySearch);
  }, [querySearch]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const setCategory = (value: string) => {
    setCategoryState(value);
    setPage(1);
  };

  const setMinPriceInput = (value: string) => {
    setMinPriceInputState(value);
    setPage(1);
  };

  const setMaxPriceInput = (value: string) => {
    setMaxPriceInputState(value);
    setPage(1);
  };

  const setInStockOnly = (value: boolean) => {
    setInStockOnlyState(value);
    setPage(1);
  };

  const resetFilters = () => {
    setSearchInput("");
    setSearch("");
    setCategoryState("");
    setMinPriceInputState("");
    setMaxPriceInputState("");
    setInStockOnlyState(false);
    setSort("featured");
    setPage(1);
  };

  const minPrice = useMemo(() => {
    const value = Number(minPriceInput);
    return Number.isFinite(value) && minPriceInput !== "" ? value : undefined;
  }, [minPriceInput]);

  const maxPrice = useMemo(() => {
    const value = Number(maxPriceInput);
    return Number.isFinite(value) && maxPriceInput !== "" ? value : undefined;
  }, [maxPriceInput]);

  const {
    data: listing,
    isLoading,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ["products", "listing", { search, category, minPrice, maxPrice, inStockOnly, page }],
    queryFn: () =>
      fetchProductListing({
        search: search || undefined,
        category: category || undefined,
        min_price: minPrice,
        max_price: maxPrice,
        in_stock: inStockOnly || undefined,
        page,
      }),
  });

  const products = useMemo(() => listing?.results ?? [], [listing?.results]);
  const visibleProducts = useMemo(() => sortProducts(products, sort), [products, sort]);
  const hasPrevious = Boolean(listing?.previous);
  const hasNext = Boolean(listing?.next);
  const activeFilters = useMemo(() => {
    const filters: Array<{ key: string; label: string }> = [];
    if (search) filters.push({ key: "search", label: `Search: ${search}` });
    if (category) filters.push({ key: "category", label: `Category: ${category}` });
    if (minPriceInput) filters.push({ key: "min", label: `Min Rs. ${minPriceInput}` });
    if (maxPriceInput) filters.push({ key: "max", label: `Max Rs. ${maxPriceInput}` });
    if (inStockOnly) filters.push({ key: "stock", label: "In stock" });
    return filters;
  }, [category, inStockOnly, maxPriceInput, minPriceInput, search]);
  const activeFilterCount = activeFilters.length;

  const removeFilter = (key: string) => {
    if (key === "search") {
      setSearchInput("");
      setSearch("");
    }
    if (key === "category") setCategoryState("");
    if (key === "min") setMinPriceInputState("");
    if (key === "max") setMaxPriceInputState("");
    if (key === "stock") setInStockOnlyState(false);
    setPage(1);
  };

  const handleAddProduct = async (product: Product) => {
    await addToCart(product.id, 1, {
      id: product.id,
      name: product.name,
      slug: product.slug,
      sku: product.sku,
      price: product.price,
      stock_quantity: product.stock_quantity,
      is_active: product.is_active,
      is_refurbished: product.is_refurbished,
      condition_grade: product.condition_grade,
      category_name: product.category_name,
      image_url: product.image_url_card ?? product.image_url ?? null,
      image_url_card: product.image_url_card ?? null,
    });
    openDrawer();
  };

  const filterPanel = (
    <FilterPanel
      searchInput={searchInput}
      setSearchInput={setSearchInput}
      category={category}
      setCategory={setCategory}
      minPriceInput={minPriceInput}
      setMinPriceInput={setMinPriceInput}
      maxPriceInput={maxPriceInput}
      setMaxPriceInput={setMaxPriceInput}
      inStockOnly={inStockOnly}
      setInStockOnly={setInStockOnly}
      resetFilters={resetFilters}
      activeFilterCount={activeFilterCount}
    />
  );

  return (
    <section className="space-y-6">
      <div className="rounded-3xl border border-surface-200 bg-gradient-to-br from-white via-primary-50 to-surface-50 p-5 shadow-sm dark:border-surface-800 dark:from-surface-900 dark:via-surface-900 dark:to-neutral-950 sm:p-6">
        <nav aria-label="Breadcrumb" className="mb-4 text-sm text-surface-500 dark:text-surface-400">
          <Link href="/" className="font-medium hover:text-primary-700 dark:hover:text-primary-300">
            Home
          </Link>
          <span className="mx-2">/</span>
          <span className="font-semibold text-surface-800 dark:text-surface-100">Products</span>
        </nav>
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 text-xs font-bold uppercase tracking-wide text-primary-700 shadow-sm dark:bg-surface-950/80 dark:text-primary-300">
              <PackageSearch className="h-3.5 w-3.5" aria-hidden="true" />
              Product discovery
            </p>
            <h1 className="mt-4 text-3xl font-black tracking-tight text-surface-950 dark:text-white sm:text-4xl">
              Browse products with less friction.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-surface-600 dark:text-surface-300 sm:text-base">
              Search, filter, and sort premium picks while keeping ready-to-ship and secure-shopping signals visible.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm sm:flex">
            <div className="rounded-2xl bg-white/80 p-3 shadow-sm dark:bg-surface-950/70">
              <Truck className="h-4 w-4 text-primary-600" aria-hidden="true" />
              <p className="mt-1 font-bold text-surface-950 dark:text-white">Fast delivery</p>
            </div>
            <div className="rounded-2xl bg-white/80 p-3 shadow-sm dark:bg-surface-950/70">
              <RotateCcw className="h-4 w-4 text-success-600" aria-hidden="true" />
              <p className="mt-1 font-bold text-surface-950 dark:text-white">Easy returns</p>
            </div>
          </div>
        </div>
      </div>

      <div className="sticky top-[var(--store-sticky-top)] z-30 -mx-4 border-y border-surface-200 bg-white/95 px-4 py-3 backdrop-blur dark:border-surface-800 dark:bg-neutral-950/95 sm:-mx-6 sm:px-6 xl:hidden">
        <div className="flex items-center gap-2">
          <Sheet>
            <SheetTrigger asChild>
              <Button type="button" variant="outline" className="flex-1 rounded-full">
                <SlidersHorizontal className="mr-2 h-4 w-4" aria-hidden="true" />
                Filters {activeFilterCount ? `(${activeFilterCount})` : ""}
              </Button>
            </SheetTrigger>
            <SheetContent side="bottom" className="max-h-[min(88dvh,720px)] overflow-y-auto rounded-t-3xl p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
              <SheetHeader>
                <SheetTitle>Refine products</SheetTitle>
              </SheetHeader>
              <div className="mt-5">{filterPanel}</div>
              <SheetClose className="right-5 top-5" />
            </SheetContent>
          </Sheet>
          <label className="sr-only" htmlFor="mobile-product-sort">
            Sort products
          </label>
          <select
            id="mobile-product-sort"
            value={sort}
            onChange={(event) => setSort(event.target.value as SortValue)}
            className="h-11 rounded-full border border-surface-300 bg-white px-3 text-sm font-semibold text-surface-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100"
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[300px_1fr]">
        <aside className="hidden xl:block">
          <div className="sticky top-36 rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900">
            {filterPanel}
          </div>
        </aside>

        <div className="space-y-5">
          <div className="rounded-3xl border border-surface-200 bg-white p-4 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-semibold text-surface-950 dark:text-white">
                  {listing ? `${listing.count} products found` : "Finding products"}
                </p>
                <p className="text-xs text-surface-500 dark:text-surface-400">
                  {search ? `Results for "${search}"` : "Explore the current catalog"}
                  {isFetching && !isLoading ? " - refreshing" : ""}
                </p>
              </div>
              <div className="hidden items-center gap-2 xl:flex">
                <label htmlFor="product-sort" className="text-sm font-semibold text-surface-700 dark:text-surface-200">
                  Sort by
                </label>
                <select
                  id="product-sort"
                  value={sort}
                  onChange={(event) => setSort(event.target.value as SortValue)}
                  className="h-10 rounded-full border border-surface-300 bg-white px-3 text-sm font-semibold text-surface-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:border-surface-700 dark:bg-surface-950 dark:text-surface-100"
                >
                  {sortOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="mt-4">
              <ActiveFilterChips filters={activeFilters} onRemove={removeFilter} onClear={resetFilters} />
            </div>
          </div>

          {isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <ProductCardSkeleton key={index} />
              ))}
            </div>
          ) : null}

          {isError ? (
            <ErrorState
              title="Unable to load products"
              description="The catalog did not respond cleanly. Retry once, or adjust filters after the catalog reconnects."
              onRetry={() => void refetch()}
              isRetrying={isFetching}
            />
          ) : null}

          {!isLoading && !isError && visibleProducts.length === 0 ? (
            <EmptyState
              eyebrow="No matches"
              title="No products found"
              description="Try clearing a filter, widening the price range, or searching for a broader category."
              icon={<PackageSearch className="h-7 w-7" aria-hidden="true" />}
              action={
                <Button type="button" className="rounded-full" onClick={resetFilters}>
                  Reset filters
                </Button>
              }
              secondaryAction={
                <Button asChild variant="secondary" className="rounded-full">
                  <Link href="/">Explore featured</Link>
                </Button>
              }
            />
          ) : null}

          {visibleProducts.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3" aria-label="Product results">
              {visibleProducts.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  href={`/products/${product.slug}`}
                  onAddToCart={() => {
                    void handleAddProduct(product);
                  }}
                  isAdding={isMutating}
                />
              ))}
            </div>
          ) : null}

          <div className="flex flex-col gap-3 rounded-3xl border border-surface-200 bg-white p-4 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-surface-500 dark:text-surface-400">
              {listing ? `Page ${page} - showing ${visibleProducts.length} of ${listing.count}` : ""}
            </p>
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 sm:flex">
              <Button
                type="button"
                variant="outline"
                className="rounded-full"
                disabled={!hasPrevious || isFetching}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                <ChevronLeft className="mr-1 h-4 w-4" aria-hidden="true" />
                Previous
              </Button>
              <span className="text-center text-sm font-semibold text-surface-700 dark:text-surface-200">Page {page}</span>
              <Button
                type="button"
                variant="outline"
                className="rounded-full"
                disabled={!hasNext || isFetching}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
                <ChevronRight className="ml-1 h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function ProductsPage() {
  return (
    <Suspense fallback={<LoadingSkeleton variant="page" count={6} />}>
      <ProductsContent />
    </Suspense>
  );
}
