from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_alter_user_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("token_refresh_attempt", "Token Refresh Attempt"), ("token_refresh_failed", "Token Refresh Failed"), ("token_refresh_success", "Token Refresh Success"), ("login_attempt", "Login Attempt"), ("login_failed", "Login Failed"), ("login_success", "Login Success")], max_length=40)),
                ("request_id", models.CharField(blank=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="auth_events", to="users.user")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="authevent",
            index=models.Index(fields=["event_type", "created_at"], name="users_authe_event_t_8b91d8_idx"),
        ),
        migrations.AddIndex(
            model_name="authevent",
            index=models.Index(fields=["user", "created_at"], name="users_authe_user_id_22f99b_idx"),
        ),
    ]
