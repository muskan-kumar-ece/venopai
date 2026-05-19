from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.utils.text import slugify


TRANSFORM_PRESETS = {
    "thumbnail": {"width": 160, "height": 160, "crop": "fill", "gravity": "auto"},
    "card": {"width": 640, "height": 480, "crop": "fill", "gravity": "auto"},
    "detail": {"width": 1200, "height": 1200, "crop": "fit"},
}


def is_cloudinary_configured():
    return bool(
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    )


def validate_product_image_upload(uploaded_file):
    max_bytes = settings.PRODUCT_IMAGE_MAX_UPLOAD_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(f"Image must be {settings.PRODUCT_IMAGE_MAX_UPLOAD_MB}MB or smaller.")

    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
    if content_type not in settings.PRODUCT_IMAGE_ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(settings.PRODUCT_IMAGE_ALLOWED_CONTENT_TYPES)
        raise ValidationError(f"Unsupported image type. Allowed types: {allowed}.")

    try:
        width, height = get_image_dimensions(uploaded_file)
    finally:
        uploaded_file.seek(0)

    if not width or not height:
        raise ValidationError("Upload must be a valid image.")
    if width < 320 or height < 320:
        raise ValidationError("Product images must be at least 320x320 pixels.")
    return width, height


def validate_product_image_url(value):
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ValidationError("Only HTTPS image URLs are allowed.")
    if not parsed.netloc:
        raise ValidationError("Image URL must include a valid host.")

    allowed_hosts = set(settings.PRODUCT_IMAGE_ALLOWED_HOSTS)
    if settings.CLOUDINARY_CLOUD_NAME:
        allowed_hosts.add("res.cloudinary.com")
    if allowed_hosts and parsed.hostname not in allowed_hosts:
        allowed = ", ".join(sorted(allowed_hosts))
        raise ValidationError(f"Image host is not allowed. Allowed hosts: {allowed}.")
    return value


def upload_product_image_to_cloudinary(uploaded_file, product):
    if not is_cloudinary_configured():
        raise ValidationError("Cloudinary is not configured for product image uploads.")

    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError as exc:
        raise ValidationError("Cloudinary package is not installed.") from exc

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=settings.CLOUDINARY_SECURE,
    )

    public_slug = slugify(product.sku or product.slug or product.name) or f"product-{product.id}"
    folder = settings.CLOUDINARY_PRODUCT_FOLDER.strip("/")
    result = cloudinary.uploader.upload(
        uploaded_file,
        folder=folder,
        public_id=public_slug,
        unique_filename=True,
        overwrite=False,
        resource_type="image",
        allowed_formats=["jpg", "jpeg", "png", "webp"],
        quality_analysis=True,
        context={"product_id": str(product.id), "sku": product.sku},
    )
    return result


def build_cloudinary_url(public_id, preset=None):
    if not public_id:
        return None
    try:
        from cloudinary import CloudinaryImage
    except ImportError:
        return None

    options = {
        "secure": True,
        "fetch_format": "auto",
        "quality": "auto",
        "dpr": "auto",
    }
    if preset:
        options.update(TRANSFORM_PRESETS[preset])
    return CloudinaryImage(public_id).build_url(**options)
