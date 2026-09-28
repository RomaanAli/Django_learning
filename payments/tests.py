"""Basic tests for the Stripe payments integration.

The webhook handler is exercised without any network call: a fake session
dict is passed straight to the internal handler, and we assert that a single
paid event enrolls the student exactly once (idempotent). The full HTTP
webhook endpoint is also tested with a locally-signed payload.
"""

import hashlib
import hmac
import json
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from courses.models import Course, Enrollment
from payments.models import Payment
from payments.views import StripeWebhookView

User = get_user_model()


def _signed_event_payload(secret, event_payload):
    """Build (payload, Stripe-Signature header) exactly like Stripe does."""
    payload = json.dumps(event_payload).encode()
    stamp = str(int(time.time())).encode()
    signed = hmac.new(secret.encode(), stamp + b"." + payload, hashlib.sha256).hexdigest()
    return payload, f"t={stamp.decode()},v1={signed}"


class StripeWebhookHandlingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="student", email="student@example.com", password="x"
        )
        cls.course = Course.objects.create(
            title="Django Basics", price="19.99", is_published=True
        )

    def _session(self, status="paid", session_id="cs_test_123"):
        return {
            "id": session_id,
            "payment_status": status,
            "payment_intent": "pi_test_456",
            "currency": "usd",
            "amount_total": 1999,
            "metadata": {
                "user_id": str(self.user.pk),
                "course_id": str(self.course.pk),
            },
        }

    def test_paid_session_enrolls_and_records_payment(self):
        StripeWebhookView._handle_session_completed(self._session())

        self.assertTrue(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())
        payment = Payment.objects.get(stripe_session_id="cs_test_123")
        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertEqual(payment.amount, Decimal("19.99"))
        self.assertEqual(payment.currency, "usd")

    def test_webhook_is_idempotent(self):
        # Delivering the SAME event twice must not create a second enrollment.
        StripeWebhookView._handle_session_completed(self._session())
        StripeWebhookView._handle_session_completed(self._session())

        self.assertEqual(
            Enrollment.objects.filter(student=self.user, course=self.course).count(), 1
        )
        self.assertEqual(Payment.objects.count(), 1)

    def test_unpaid_session_does_not_enroll(self):
        StripeWebhookView._handle_session_completed(self._session(status="unpaid"))
        self.assertFalse(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())
        self.assertEqual(Payment.objects.count(), 0)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret")
    def test_webhook_http_endpoint(self):
        event = {
            "id": "evt_test_1",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {"object": self._session()},
        }
        payload, signature = _signed_event_payload("whsec_test_secret", event)
        response = Client().post(
            "/webhooks/stripe/",
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret")
    def test_webhook_http_endpoint_rejects_bad_signature(self):
        event = {
            "id": "evt_test_2",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {"object": self._session()},
        }
        payload, _ = _signed_event_payload("whsec_wrong_secret", event)
        response = Client().post(
            "/webhooks/stripe/",
            payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=0,v1=bogus",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())


class PaymentPageTests(TestCase):
    """The checkout page itself (the nice-looking payment page)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="x"
        )
        cls.paid = Course.objects.create(
            title="Paid Course", price="49.00", is_published=True
        )
        cls.free = Course.objects.create(
            title="Free Course", price="0.00", is_published=True
        )

    def test_confirm_page_requires_login(self):
        response = self.client.get(f"/payments/confirm/{self.paid.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    def test_confirm_page_renders_summary(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/payments/confirm/{self.paid.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Secure Checkout")
        self.assertContains(response, "Paid Course")
        self.assertContains(response, "49.00")
        # The secret key must never leak into the HTML.
        self.assertNotContains(response, "sk_test_dummy")
        self.assertNotContains(response, "pk_test")

    def test_confirm_page_warns_when_keys_missing(self):
        self.client.force_login(self.user)
        with override_settings(STRIPE_SECRET_KEY=""):
            response = self.client.get(f"/payments/confirm/{self.paid.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payments are not configured yet")

    def test_checkout_without_keys_does_not_create_payment(self):
        self.client.force_login(self.user)
        with override_settings(STRIPE_SECRET_KEY=""):
            response = self.client.post(f"/payments/checkout/{self.paid.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Payment.objects.count(), 0)

    def test_free_course_enroll_still_works(self):
        self.client.force_login(self.user)
        response = self.client.post(f"/courses/{self.free.pk}/enroll/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Enrollment.objects.filter(
            student=self.user, course=self.free
        ).exists())