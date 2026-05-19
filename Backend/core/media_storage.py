from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class CloudinaryMediaStorage(Storage):
    """Small Cloudinary-backed storage for optional Django default storage use.

    Product images are uploaded explicitly through the products app so the API
    can persist public IDs and serve transformed URLs. This storage keeps other
    future media fields production-safe when MEDIA_STORAGE_BACKEND=cloudinary.
    """

    def _require_cloudinary(self):
        try:
            import cloudinary.uploader
        except ImportError as exc:
            raise RuntimeError("Install the cloudinary package to use CloudinaryMediaStorage.") from exc
        return cloudinary.uploader

    def _save(self, name, content):
        uploader = self._require_cloudinary()
        result = uploader.upload(content, public_id=name, overwrite=False, resource_type="image")
        return result["public_id"]

    def exists(self, name):
        return False

    def url(self, name):
        try:
            from cloudinary import CloudinaryImage
        except ImportError as exc:
            raise RuntimeError("Install the cloudinary package to use CloudinaryMediaStorage.") from exc
        return CloudinaryImage(name).build_url(secure=True)
