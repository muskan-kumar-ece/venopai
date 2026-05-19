from django.contrib import admin
from django.db.models import F
from django.utils.html import format_html

from .models import Category, FlashSale, Inventory, Product, ProductImage, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active", "updated_at")
    search_fields = ("name", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "inventory_alert", "is_active", "updated_at")
    list_filter = ("is_active", "is_refurbished", "category", "created_at")
    search_fields = ("name", "sku", "description")
    list_select_related = ("category", "inventory")

    @admin.display(description="Inventory Alert")
    def inventory_alert(self, obj):
        inventory = getattr(obj, "inventory", None)
        if not inventory:
            return format_html('<span style="color:#d97706;font-weight:600;">No inventory</span>')
        available = max(inventory.quantity - inventory.reserved_quantity, 0)
        if available < inventory.reorder_level:
            return format_html('<span style="color:#dc2626;font-weight:700;">Low ({})</span>', available)
        return format_html('<span style="color:#16a34a;font-weight:600;">Healthy ({})</span>', available)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "sort_order", "provider", "dimensions", "updated_at")
    list_filter = ("is_primary", "updated_at")
    search_fields = ("product__name", "product__sku", "alt_text", "cloudinary_public_id", "image_url")
    list_select_related = ("product",)
    readonly_fields = ("cloudinary_public_id", "width", "height", "bytes", "format", "preview")

    @admin.display(description="Provider")
    def provider(self, obj):
        return "Cloudinary" if obj.cloudinary_public_id else "External URL"

    @admin.display(description="Dimensions")
    def dimensions(self, obj):
        if obj.width and obj.height:
            return f"{obj.width}x{obj.height}"
        return "-"

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj.image_url:
            return "-"
        return format_html('<img src="{}" alt="" style="max-width:180px;max-height:180px;" />', obj.image_url)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "reserved_quantity", "reorder_level", "available_stock", "stock_alert")
    list_filter = ("updated_at",)
    search_fields = ("product__name", "product__sku")
    list_select_related = ("product",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product").annotate(
            available=F("quantity") - F("reserved_quantity")
        )

    @admin.display(ordering="available", description="Available")
    def available_stock(self, obj):
        return max(obj.available, 0)

    @admin.display(description="Alert")
    def stock_alert(self, obj):
        available = max(obj.available, 0)
        if available < obj.reorder_level:
            return format_html('<span style="color:#dc2626;font-weight:700;">Reorder</span>')
        return format_html('<span style="color:#16a34a;font-weight:600;">OK</span>')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "user", "rating", "title", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__email", "title", "comment")
    list_select_related = ("product", "user")


@admin.register(FlashSale)
class FlashSaleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "discount_percentage",
        "start_time",
        "end_time",
        "stock_limit",
        "sold_quantity",
    )
    list_filter = ("start_time", "end_time")
    search_fields = ("product__name", "product__sku")
    list_select_related = ("product",)
