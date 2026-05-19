from rest_framework import serializers

from products.models import Product
from products.media import build_cloudinary_url

from .models import Wishlist


def get_product_image_url(product):
    primary_image = product.images.filter(is_primary=True).first()
    if primary_image:
        return build_cloudinary_url(primary_image.cloudinary_public_id, "card") or primary_image.image_url
    fallback_image = product.images.first()
    if fallback_image:
        return build_cloudinary_url(fallback_image.cloudinary_public_id, "card") or fallback_image.image_url
    return None


class WishlistProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'image', 'slug')

    def get_image(self, obj):
        return get_product_image_url(obj)


class WishlistItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=12, decimal_places=2, read_only=True)
    image_url = serializers.SerializerMethodField()
    product_details = WishlistProductSerializer(source='product', read_only=True)

    class Meta:
        model = Wishlist
        fields = (
            'id',
            'product',
            'product_name',
            'product_price',
            'image_url',
            'product_details',
            'created_at',
        )
        read_only_fields = fields

    def get_image_url(self, obj):
        return get_product_image_url(obj.product)


class WishlistCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
