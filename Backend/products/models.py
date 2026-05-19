from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    sku = models.CharField(max_length=64, unique=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_refurbished = models.BooleanField(default=False)
    condition_grade = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_active", "created_at"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["price"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(stock_quantity__gte=0),
                name="product_stock_quantity_non_negative",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField(max_length=500)
    cloudinary_public_id = models.CharField(max_length=255, blank=True, db_index=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    bytes = models.PositiveIntegerField(null=True, blank=True)
    format = models.CharField(max_length=24, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["is_primary"]),
        ]

    def __str__(self):
        return f"{self.product.name} image"


class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["quantity"]),
        ]

    def __str__(self):
        return f"{self.product.name} inventory"


class Review(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=255)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_review_per_user_product"),
        ]
        indexes = [
            models.Index(fields=["product", "created_at"]),
            models.Index(fields=["user", "product"]),
        ]

    def __str__(self):
        return f"Review {self.id} - {self.product.name}"


class FlashSale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="flash_sales")
    discount_percentage = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    stock_limit = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    sold_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("start_time", "-created_at")
        indexes = [
            models.Index(fields=["start_time", "end_time"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"Flash Sale - {self.product.name} ({self.discount_percentage}% off)"

    def has_stock_remaining(self):
        return self.sold_quantity < self.stock_limit

    def is_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time and self.has_stock_remaining()

    def discounted_price(self):
        discount_factor = Decimal(100 - self.discount_percentage) / Decimal("100")
        return (self.product.price * discount_factor).quantize(Decimal("0.01"))

    def remaining_stock(self):
        return max(self.stock_limit - self.sold_quantity, 0)

    def countdown_seconds(self):
        now = timezone.now()
        if now < self.start_time:
            return int((self.start_time - now).total_seconds())
        if self.is_active():
            return int((self.end_time - now).total_seconds())
        return 0
