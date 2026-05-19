from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from products.models import ProductImage


class Command(BaseCommand):
    help = "Audit product images and backfill Cloudinary public IDs for existing Cloudinary URLs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write",
            action="store_true",
            help="Persist detected Cloudinary public IDs.",
        )

    def handle(self, *args, **options):
        write = options["write"]
        cloud_name = settings.CLOUDINARY_CLOUD_NAME
        cloudinary_prefix = f"/{cloud_name}/image/upload/"
        cloudinary_count = 0
        backfilled_count = 0
        external_count = 0
        missing_count = 0

        for image in ProductImage.objects.select_related("product").order_by("id"):
            if not image.image_url:
                missing_count += 1
                self.stdout.write(f"[missing] image_id={image.id} product_id={image.product_id}")
                continue

            parsed = urlparse(image.image_url)
            if parsed.hostname == "res.cloudinary.com" and cloud_name and parsed.path.startswith(cloudinary_prefix):
                cloudinary_count += 1
                public_id = parsed.path.removeprefix(cloudinary_prefix)
                parts = public_id.split("/")
                if parts and parts[0].startswith("v") and parts[0][1:].isdigit():
                    public_id = "/".join(parts[1:])
                public_id = public_id.rsplit(".", 1)[0]
                if public_id and public_id != image.cloudinary_public_id:
                    backfilled_count += 1
                    self.stdout.write(f"[cloudinary] image_id={image.id} public_id={public_id}")
                    if write:
                        image.cloudinary_public_id = public_id
                        image.save(update_fields=["cloudinary_public_id", "updated_at"])
                continue

            external_count += 1
            self.stdout.write(f"[external] image_id={image.id} host={parsed.hostname} url={image.image_url}")

        self.stdout.write(
            self.style.SUCCESS(
                "Product image audit complete: "
                f"cloudinary={cloudinary_count}, backfillable={backfilled_count}, "
                f"external={external_count}, missing={missing_count}, write={write}"
            )
        )
