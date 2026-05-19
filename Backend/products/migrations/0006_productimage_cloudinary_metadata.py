from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_product_products_pr_is_acti_defdf1_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productimage",
            name="bytes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="productimage",
            name="cloudinary_public_id",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="productimage",
            name="format",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="productimage",
            name="height",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="productimage",
            name="width",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
