from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_authevent"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="authevent",
            index=models.Index(fields=["request_id", "created_at"], name="users_authe_request_2c7dd8_idx"),
        ),
    ]
