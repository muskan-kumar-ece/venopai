from difflib import SequenceMatcher
import hashlib
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Avg, Count, Q, Value, Prefetch
from django.db.models.functions import Coalesce
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, parsers, permissions, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.throttles import ReviewRateThrottle
from core.cache_utils import cache_get, cache_set

from .models import Category, FlashSale, Inventory, Product, ProductImage, Review
from .permissions import IsAdminOrReadOnly
from .serializers import (
    CategorySerializer,
    InventorySerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ProductSearchResultSerializer,
    ProductSerializer,
    ProductSuggestionSerializer,
    ReviewSerializer,
    FlashSaleSerializer,
)


def normalize_search_query(value):
    return value.strip().lower()


class ReviewPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductFilterSet(filters.FilterSet):
    category = filters.CharFilter(method="filter_category")
    price = filters.NumberFilter(field_name="price")
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    stock_quantity = filters.NumberFilter(field_name="stock_quantity")
    is_active = filters.BooleanFilter(field_name="is_active")
    in_stock = filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ["category", "price", "stock_quantity", "is_active"]

    def filter_category(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(category_id=int(value))
        return queryset.filter(category__slug=value)

    def filter_in_stock(self, queryset, name, value):
        if value is None:
            return queryset
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset.filter(stock_quantity=0)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        cache_key = "category_list:active"
        cached = cache_get(cache_key)
        if cached is not None:
            return Response(cached)
        queryset = self.filter_queryset(self.get_queryset())
        if not request.user.is_authenticated or not request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        cache_set(cache_key, serializer.data, timeout=600)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilterSet
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Return the lightweight list serializer for collection responses."""
        if self.action == "list":
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related("category", "inventory").prefetch_related("images").annotate(
            average_rating=Coalesce(Avg("reviews__rating"), Value(0.0)),
            reviews_count=Count("reviews"),
        )
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        return queryset.filter(is_active=True)

    def _product_list_cache_key(self, request):
        sorted_query_params = urlencode(sorted(request.query_params.lists()), doseq=True)
        page_number = request.query_params.get("page", "1")
        key_source = f"{request.path}|{sorted_query_params}|page={page_number}"
        key_hash = hashlib.sha256(key_source.encode("utf-8")).hexdigest()
        return f"product_list:{key_hash}"

    def list(self, request, *args, **kwargs):
        if request.method != "GET":
            return super().list(request, *args, **kwargs)

        cache_key = self._product_list_cache_key(request)
        try:
            cached = cache_get(cache_key)
            if cached is not None:
                return Response(cached)
        except Exception:
            pass

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)

        try:
            cache_set(cache_key, response.data, timeout=settings.CACHE_TTL_PRODUCT_LIST)
        except Exception:
            pass
        return response

    def retrieve(self, request, *args, **kwargs):
        if request.method != "GET":
            return super().retrieve(request, *args, **kwargs)

        cache_key = f"product_detail:{kwargs.get('pk')}"
        try:
            cached = cache_get(cache_key)
            if cached is not None:
                return Response(cached)
        except Exception:
            pass

        response = super().retrieve(request, *args, **kwargs)
        try:
            cache_set(cache_key, response.data, timeout=settings.CACHE_TTL_PRODUCT_LIST * 2)
        except Exception:
            pass
        return response


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.select_related("product")
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser, parsers.FormParser]


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.select_related("product")
    serializer_class = InventorySerializer
    permission_classes = [IsAdminOrReadOnly]


class FlashSaleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FlashSale.objects.select_related("product").filter(product__is_active=True)
    serializer_class = FlashSaleSerializer
    permission_classes = [permissions.AllowAny]


class ProductReviewListView(ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = ReviewPagination

    def get_queryset(self):
        return Review.objects.filter(product_id=self.kwargs["product_id"]).select_related("user", "product")


class ReviewViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_throttles(self):
        if self.action == "create":
            return [ReviewRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        queryset = Review.objects.select_related("user", "product")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.user_id != self.request.user.id:
            raise PermissionDenied("You can only edit your own review.")
        serializer.save()


class ProductSearchView(GenericAPIView):
    # Threshold chosen so weak fuzzy-only matches are filtered out while exact/near name-category matches remain.
    MIN_SEARCH_SCORE = 5.0
    serializer_class = ProductSearchResultSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = ProductPagination

    @staticmethod
    def _max_similarity(query, text):
        query = query.lower()
        text = text.lower()
        candidates = [text] + text.split()
        return max(SequenceMatcher(None, query, candidate).ratio() for candidate in candidates if candidate)

    @staticmethod
    def _candidate_filter(query):
        if len(query) < 3:
            chunks = {query}
        else:
            chunks = {query[i : i + 3] for i in range(len(query) - 2)}
        lookup = Q(name__icontains=query) | Q(category__name__icontains=query)
        for chunk in chunks:
            if chunk:
                lookup |= Q(name__icontains=chunk) | Q(category__name__icontains=chunk)
        return lookup

    def get(self, request):
        query = normalize_search_query(request.query_params.get("q", ""))
        if not query:
            return Response({"count": 0, "next": None, "previous": None, "results": []})

        products = (
            Product.objects.select_related("category")
            .only("id", "name", "slug", "price", "category_id", "category__name", "is_active")
            .filter(is_active=True)
            .filter(self._candidate_filter(query))
        )
        ranked = []
        for product in products:
            name = product.name.lower()
            category_name = product.category.name.lower()
            score = 0.0

            if query in name:
                score += 10.0
            if query in category_name:
                score += 8.0

            score += self._max_similarity(query, name) * 6.0
            score += self._max_similarity(query, category_name) * 4.0

            if score >= self.MIN_SEARCH_SCORE:
                product.relevance_score = round(score, 3)
                ranked.append(product)

        ranked.sort(key=lambda p: (-p.relevance_score, p.id))
        page = self.paginate_queryset(ranked)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class ProductSearchSuggestionsView(GenericAPIView):
    # Lower threshold than full search to keep autocomplete responsive for partial inputs.
    MIN_SUGGESTION_SCORE = 2.5
    MAX_SUGGESTIONS = 10
    serializer_class = ProductSuggestionSerializer
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def _suggestion_score(query, product):
        query = query.lower()
        name = product.name.lower()
        category_name = product.category.name.lower()
        score = 0.0

        if name.startswith(query):
            score += 12.0
        if category_name.startswith(query):
            score += 6.0
        if query in name:
            score += 8.0
        if query in category_name:
            score += 4.0

        score += SequenceMatcher(None, query, name).ratio() * 5.0
        score += SequenceMatcher(None, query, category_name).ratio() * 3.0
        return score

    def get(self, request):
        query = normalize_search_query(request.query_params.get("q", ""))
        if not query:
            return Response([])

        products = (
            Product.objects.select_related("category")
            .only("id", "name", "category_id", "category__name", "is_active")
            .filter(is_active=True)
            .filter(ProductSearchView._candidate_filter(query))
        )
        scored = []
        for product in products:
            score = self._suggestion_score(query, product)
            if score >= self.MIN_SUGGESTION_SCORE:
                scored.append((score, product))

        scored.sort(key=lambda item: (-item[0], item[1].id))
        top_products = [item[1] for item in scored[: self.MAX_SUGGESTIONS]]
        serializer = self.get_serializer(top_products, many=True)
        return Response(serializer.data)


class HomeCatalogView(GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = "homepage:catalog:v1"
        cached = cache_get(cache_key)
        if cached is not None:
            return Response(cached)

        featured_products = list(
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related(Prefetch("images"))
            .order_by("-created_at")[:8]
        )
        featured_payload = ProductListSerializer(featured_products, many=True).data
        categories = list(Category.objects.filter(is_active=True).order_by("name")[:12])
        category_payload = CategorySerializer(categories, many=True).data
        payload = {
            "featured_products": featured_payload,
            "categories": category_payload,
        }
        cache_set(cache_key, payload, timeout=300)
        return Response(payload)
