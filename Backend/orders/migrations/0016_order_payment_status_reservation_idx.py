from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0015_inventory_reservation_and_audit"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["payment_status", "reservation_expires_at"], name="orders_orde_payment_a61b6e_idx"),
        ),
    ]
