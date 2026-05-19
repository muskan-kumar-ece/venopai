from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_product_products_pr_is_acti_defdf1_idx_and_more"),
        ("orders", "0014_order_source_cart"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="reservation_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="reservation_released_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("pending_payment", "Pending Payment"),
                    ("payment_processing", "Payment Processing"),
                    ("pending", "Pending"),
                    ("paid", "Paid"),
                    ("failed", "Failed"),
                    ("cancelled", "Cancelled"),
                    ("refunded", "Refunded"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending_payment", "Pending Payment"),
                    ("payment_processing", "Payment Processing"),
                    ("paid", "Paid"),
                    ("failed", "Failed"),
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("payment_failed", "Payment Failed"),
                    ("shipped", "Shipped"),
                    ("delivered", "Delivered"),
                    ("cancelled", "Cancelled"),
                    ("refunded", "Refunded"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="InventoryAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_reference", models.CharField(blank=True, max_length=255)),
                ("reason", models.CharField(choices=[("reserve", "Reserve"), ("release", "Release"), ("finalize", "Finalize"), ("adjustment", "Adjustment")], max_length=20)),
                ("before_quantity", models.IntegerField()),
                ("after_quantity", models.IntegerField()),
                ("delta", models.IntegerField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inventory_audits", to="orders.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_audits", to="products.product")),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="InventoryReservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("status", models.CharField(choices=[("active", "Active"), ("finalized", "Finalized"), ("released", "Released"), ("expired", "Expired")], db_index=True, default="active", max_length=20)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("released_at", models.DateTimeField(blank=True, null=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_reservations", to="orders.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_reservations", to="products.product")),
            ],
        ),
        migrations.AddIndex(
            model_name="inventoryauditlog",
            index=models.Index(fields=["product", "created_at"], name="orders_inve_product_11591e_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryauditlog",
            index=models.Index(fields=["order", "created_at"], name="orders_inve_order_i_178eec_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryauditlog",
            index=models.Index(fields=["reason", "created_at"], name="orders_inve_reason_935df4_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryreservation",
            index=models.Index(fields=["order", "status"], name="orders_inve_order_i_14c89d_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryreservation",
            index=models.Index(fields=["product", "status"], name="orders_inve_product_78f9d5_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryreservation",
            index=models.Index(fields=["status", "expires_at"], name="orders_inve_status_93a644_idx"),
        ),
        migrations.AddConstraint(
            model_name="inventoryreservation",
            constraint=models.UniqueConstraint(fields=("order", "product"), name="unique_reservation_per_order_product"),
        ),
    ]
