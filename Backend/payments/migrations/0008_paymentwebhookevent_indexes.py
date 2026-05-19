from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0007_paymentwebhookretry"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="paymentwebhookevent",
            index=models.Index(fields=["event_type", "processed_at"], name="payments_pa_event_t_fef2d3_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentwebhookevent",
            index=models.Index(fields=["processed_at"], name="payments_pa_process_14f499_idx"),
        ),
    ]
