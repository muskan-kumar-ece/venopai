import re

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Category, FlashSale, Inventory, Product, ProductImage, Review
from .media import (
    build_cloudinary_url,
    upload_product_image_to_cloudinary,
    validate_product_image_upload,
    validate_product_image_url,
)
from orders.models import Order, OrderItem


def strip_html_tags(value: str) -> str:
    """Remove HTML/XML tags and collapse excess whitespace from a string.

    This is a lightweight defence-in-depth sanitisation step that ensures
    no raw HTML can be stored in free-text fields such as review comments or
    product descriptions, reducing XSS risk in rendered output.
    """
    clean = re.sub(r"<[^>]+>", "", value or "")
    return " ".join(clean.split())


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProductImageSerializer(serializers.ModelSerializer):
    upload_image = serializers.ImageField(write_only=True, required=False)
    image_url_thumbnail = serializers.SerializerMethodField()
    image_url_card = serializers.SerializerMethodField()
    image_url_detail = serializers.SerializerMethodField()

    def validate_image_url(self, value):
        try:
            return validate_product_image_url(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate_upload_image(self, value):
        try:
            validate_product_image_upload(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("image_url") and not attrs.get("upload_image"):
            raise serializers.ValidationError("Provide image_url or upload_image.")
        return attrs

    def create(self, validated_data):
        upload = validated_data.pop("upload_image", None)
        if upload:
            result = upload_product_image_to_cloudinary(upload, validated_data["product"])
            validated_data.update(
                image_url=result["secure_url"],
                cloudinary_public_id=result.get("public_id", ""),
                width=result.get("width"),
                height=result.get("height"),
                bytes=result.get("bytes"),
                format=result.get("format", ""),
            )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        upload = validated_data.pop("upload_image", None)
        if upload:
            product = validated_data.get("product", instance.product)
            result = upload_product_image_to_cloudinary(upload, product)
            validated_data.update(
                image_url=result["secure_url"],
                cloudinary_public_id=result.get("public_id", ""),
                width=result.get("width"),
                height=result.get("height"),
                bytes=result.get("bytes"),
                format=result.get("format", ""),
            )
        return super().update(instance, validated_data)

    def get_image_url_thumbnail(self, obj):
        return build_cloudinary_url(obj.cloudinary_public_id, "thumbnail") or obj.image_url

    def get_image_url_card(self, obj):
        return build_cloudinary_url(obj.cloudinary_public_id, "card") or obj.image_url

    def get_image_url_detail(self, obj):
        return build_cloudinary_url(obj.cloudinary_public_id, "detail") or obj.image_url

    class Meta:
        model = ProductImage
        fields = (
            "id",
            "product",
            "image_url",
            "image_url_thumbnail",
            "image_url_card",
            "image_url_detail",
            "cloudinary_public_id",
            "width",
            "height",
            "bytes",
            "format",
            "upload_image",
            "alt_text",
            "is_primary",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "image_url_thumbnail",
            "image_url_card",
            "image_url_detail",
            "cloudinary_public_id",
            "width",
            "height",
            "bytes",
            "format",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"image_url": {"required": False}}


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = (
            "id",
            "product",
            "quantity",
            "reserved_quantity",
            "reorder_level",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProductSerializer(serializers.ModelSerializer):
    """Full product serializer — used for create/update and single-object detail responses."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()
    image_url_card = serializers.SerializerMethodField()
    image_url_detail = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "slug",
            "description",
            "price",
            "sku",
            "stock_quantity",
            "is_refurbished",
            "condition_grade",
            "is_active",
            "average_rating",
            "reviews_count",
            "image_url",
            "image_url_card",
            "image_url_detail",
            "images",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_description(self, value):
        return strip_html_tags(value)

    def validate_name(self, value):
        return strip_html_tags(value)

    def _primary_image(self, obj):
        images = list(obj.images.all())
        if not images:
            return None
        return next((image for image in images if image.is_primary), images[0])

    def get_image_url(self, obj):
        image = self._primary_image(obj)
        return image.image_url if image else None

    def get_image_url_card(self, obj):
        image = self._primary_image(obj)
        if not image:
            return None
        return build_cloudinary_url(image.cloudinary_public_id, "card") or image.image_url

    def get_image_url_detail(self, obj):
        image = self._primary_image(obj)
        if not image:
            return None
        return build_cloudinary_url(image.cloudinary_public_id, "detail") or image.image_url


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer used for paginated product list responses.

    Omits ``description`` (often large) and nested inventory data to keep
    list payloads small, reducing both bandwidth and serialization overhead.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()
    image_url_card = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "slug",
            "price",
            "stock_quantity",
            "is_refurbished",
            "condition_grade",
            "is_active",
            "average_rating",
            "reviews_count",
            "image_url",
            "image_url_card",
        )
        read_only_fields = fields

    def _primary_image(self, obj):
        images = list(obj.images.all())
        if not images:
            return None
        return next((image for image in images if image.is_primary), images[0])

    def get_image_url(self, obj):
        image = self._primary_image(obj)
        return image.image_url if image else None

    def get_image_url_card(self, obj):
        image = self._primary_image(obj)
        if not image:
            return None
        return build_cloudinary_url(image.cloudinary_public_id, "card") or image.image_url


class ProductSearchResultSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    relevance_score = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "price",
            "category_name",
            "relevance_score",
        )
        read_only_fields = fields


class ProductSuggestionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "category_name",
        )
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    is_mine = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "user",
            "user_name",
            "is_mine",
            "product",
            "rating",
            "title",
            "comment",
            "created_at",
        )
        read_only_fields = ("id", "user", "user_name", "is_mine", "created_at")

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)

    def validate_title(self, value):
        return strip_html_tags(value)

    def validate_comment(self, value):
        return strip_html_tags(value)

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return attrs

        product = attrs.get("product") or getattr(self.instance, "product", None)
        if product is None:
            return attrs

        if self.instance is None:
            if Review.objects.filter(user=request.user, product=product).exists():
                raise serializers.ValidationError("You have already reviewed this product.")
            has_verified_purchase = OrderItem.objects.filter(
                order__user=request.user,
                order__payment_status=Order.PaymentStatus.PAID,
                product=product,
            ).exists()
            if not has_verified_purchase:
                raise serializers.ValidationError("Only verified buyers can review this product.")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return Review.objects.create(user=request.user, **validated_data)


class FlashSaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    original_price = serializers.DecimalField(source="product.price", max_digits=12, decimal_places=2, read_only=True)
    discounted_price = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    remaining_stock = serializers.SerializerMethodField()
    countdown_seconds = serializers.SerializerMethodField()

    class Meta:
        model = FlashSale
        fields = (
            "id",
            "product",
            "product_name",
            "discount_percentage",
            "original_price",
            "discounted_price",
            "start_time",
            "end_time",
            "stock_limit",
            "sold_quantity",
            "remaining_stock",
            "is_active",
            "countdown_seconds",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_discounted_price(self, obj):
        return obj.discounted_price()

    def get_is_active(self, obj):
        return obj.is_active()

    def get_remaining_stock(self, obj):
        return obj.remaining_stock()

    def get_countdown_seconds(self, obj):
        return obj.countdown_seconds()
