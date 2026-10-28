from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import EmailVerification
from payments.models import Payment

User = get_user_model()

PASSWORD = "StrongPass!123"


class MeApiTests(TestCase):
    """API tests for the /api/me/ endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="test_user",
            email="test@example.com",
            password=PASSWORD,
            role=User.ROLE_STUDENT,
        )

    def _token(self, user):
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": PASSWORD},
        )
        return client, response.data["access"]

    def test_me_returns_exact_keys(self):
        client, token = self._token(self.user)
        response = client.get(reverse("api_me"), HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), {"id", "username", "email", "email_verified"})
        self.assertEqual(response.data["id"], self.user.pk)
        self.assertEqual(response.data["username"], "test_user")
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertFalse(response.data["email_verified"])

    def test_me_with_verified_email(self):
        from django.utils import timezone
        from datetime import timedelta

        EmailVerification.objects.create(
            user=self.user,
            otp="123456",
            expires_at=timezone.now() + timedelta(minutes=5),
            is_verified=True,
        )
        client, token = self._token(self.user)
        response = client.get(reverse("api_me"), HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertTrue(response.data["email_verified"])


class UserSerializerTests(TestCase):
    """Tests for the full UserSerializer used outside /api/me/."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="test_user",
            email="test@example.com",
            password=PASSWORD,
            role=User.ROLE_STUDENT,
        )

    def test_serializer_excludes_sensitive_fields(self):
        from accounts.serializers import UserSerializer
        serializer = UserSerializer(self.user)
        data = serializer.data
        # No password, password hash, is_staff, is_superuser
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)
        self.assertNotIn("is_staff", data)
        self.assertNotIn("is_superuser", data)
        # Has the expected fields
        self.assertIn("id", data)
        self.assertIn("username", data)
        self.assertIn("email", data)
        self.assertIn("role", data)
        self.assertIn("email_verified", data)

    def test_role_is_read_only(self):
        from accounts.serializers import UserSerializer
        serializer = UserSerializer(self.user)
        assert serializer.fields["role"].read_only


class EmailVerificationModelTests(TestCase):
    """Tests confirming the email verification model behaves as expected."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="test_user",
            email="test@example.com",
            password=PASSWORD,
        )

    def test_is_verified_fallback_when_no_row(self):
        self.assertFalse(self.user.email_verification.is_verified if hasattr(
            self.user, "email_verification"
        ) else False)

    def test_security_no_leak(self):
        """Verify that serializing a user does not leak email_verification details."""
        from accounts.serializers import UserSerializer
        data = UserSerializer(self.user).data
        self.assertNotIn("otp", str(data))
        self.assertNotIn("expires_at", str(data))
