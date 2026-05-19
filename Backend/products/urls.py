from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, HomeCatalogView, InventoryViewSet, ProductImageViewSet, ProductReviewListView, ProductViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("images", ProductImageViewSet, basename="product-image")
router.register("inventory", InventoryViewSet, basename="inventory")
router.register("", ProductViewSet, basename="product")

urlpatterns = [
    path("home-catalog/", HomeCatalogView.as_view(), name="home-catalog"),
    path("<int:product_id>/reviews/", ProductReviewListView.as_view(), name="product-reviews"),
] + router.urls
