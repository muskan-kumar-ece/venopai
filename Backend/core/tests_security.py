from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(
    SECRET_KEY="test-secret-key-12345678901234567890",
    DEBUG=True,
)
class SecurityHardeningTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="secure-user@example.com",
            password="StrongPass123!",
            name="Secure User",
        )

    def test_security_headers_are_set(self):
        response = self.client.get("/api/v1/health/")
        self.assertIn("Content-Security-Policy", response)
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_login_lockout_after_repeated_failures(self):
        for _ in range(8):
            self.client.post(
                "/api/v1/auth/token/",
                {"email": self.user.email, "password": "wrong-password"},
                format="json",
            )

        locked = self.client.post(
            "/api/v1/auth/token/",
            {"email": self.user.email, "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(locked.status_code, 429)
        self.assertIn("Too many failed login attempts", str(locked.data))
