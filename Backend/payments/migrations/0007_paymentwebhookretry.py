from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0006_payment_payments_pa_order_i_a76289_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentWebhookRetry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(db_index=True, max_length=255)),
                ("event_type", models.CharField(max_length=100)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=5)),
                ("next_retry_at", models.DateTimeField(db_index=True)),
                ("last_error", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("success", "Success"), ("dead_letter", "Dead Letter")], db_index=True, default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("payment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="webhook_retries", to="payments.payment")),
            ],
        ),
        migrations.AddIndex(
            model_name="paymentwebhookretry",
            index=models.Index(fields=["status", "next_retry_at"], name="payments_pa_status_588b89_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentwebhookretry",
            index=models.Index(fields=["payment", "status"], name="payments_pa_payment_08c176_idx"),
        ),
    ]
