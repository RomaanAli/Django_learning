from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from courses.models import Course
from payments.models import Payment

User = get_user_model()

PASSWORD = "StrongPass!123"


class PaymentApiTests(TestCase):
    """API tests for payments (read-only)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password=PASSWORD,
        )
        self.other_user = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password=PASSWORD,
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.published = Course.objects.create(
            title="Published Course",
            description="D",
            price=0,
            is_published=True,
            instructor=self.instructor,
        )
        self.payment = Payment.objects.create(
            user=self.user,
            course=self.published,
            stripe_session_id="cs_test_1",
            stripe_payment_intent="pi_test_1",
            amount="19.99",
            currency="usd",
            status=Payment.Status.PAID,
        )

    def _token(self, user):
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": PASSWORD},
        )
        return client, response.data["access"]

    def test_payment_list_shows_only_own(self):
        client, token = self._token(self.user)
        response = client.get(reverse("api_payment_list"), HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["course"]["id"], self.published.pk)

    def test_payment_detail_own_payment(self):
        client, token = self._token(self.user)
        response = client.get(
            reverse("api_payment_detail", args=[self.payment.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["amount"], "19.99")
        self.assertEqual(response.data["currency"], "usd")

    def test_payment_detail_another_users_returns_404(self):
        client, token = self._token(self.other_user)
        response = client.get(
            reverse("api_payment_detail", args=[self.payment.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PaymentSerializerTests(TestCase):
    """Tests for the PaymentSerializer read-only fields."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password=PASSWORD,
        )
        self.course = Course.objects.create(
            title="Test Course",
            description="D",
            price=0,
            is_published=True,
            instructor=self.user,
        )
        self.payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            stripe_session_id="cs_test_1",
            stripe_payment_intent="pi_test_1",
            amount="19.99",
            currency="usd",
            status=Payment.Status.PAID,
        )

    def test_serializer_is_read_only(self):
        from payments.serializers import PaymentSerializer
        serializer = PaymentSerializer(self.payment)
        data = serializer.data
        # All fields should be read-only
        self.assertEqual(data["id"], self.payment.id)
        self.assertEqual(data["course"]["id"], self.course.id)
        self.assertEqual(data["amount"], "19.99")
        self.assertEqual(data["currency"], "usd")
        self.assertEqual(data["status"], "paid")
        self.assertIn("created_at", data)
