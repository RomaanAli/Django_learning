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
from unittest.mock import patch

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
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
        self.assertEqual(len(mail.outbox), 0)

    def test_paid_session_emails_the_student_with_course_and_price(self):
        StripeWebhookView._handle_session_completed(self._session())

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["student@example.com"])
        self.assertIn("Django Basics", email.subject)
        self.assertIn("Django Basics", email.body)
        self.assertIn("19.99", email.body)
        self.assertIn("USD", email.body)

    def test_duplicate_event_sends_only_one_email(self):
        StripeWebhookView._handle_session_completed(self._session())
        StripeWebhookView._handle_session_completed(self._session())

        self.assertEqual(len(mail.outbox), 1)

    @patch("payments.views.send_mail", side_effect=OSError("SMTP down"))
    def test_email_failure_does_not_block_enrollment(self, send_mail_mock):
        handled = StripeWebhookView._handle_session_completed(self._session())

        self.assertTrue(handled)
        self.assertTrue(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())
        send_mail_mock.assert_called_once()

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


class CheckoutSessionPayloadTests(TestCase):
    """Regression guard: the exact payload handed to Stripe.

    Stripe rejects an *empty* ``product_data.description``, which used to make
    buying a course with no description fail with a 500 message. These tests
    capture the kwargs the view sends and assert the field is omitted.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="x"
        )

    def _create_call_kwargs(self, course):
        self.client.force_login(self.user)
        with override_settings(STRIPE_SECRET_KEY="sk_test_dummy"):
            with patch("payments.views.stripe.checkout.Session.create") as create:
                create.return_value = stripe.StripeObject.construct_from(
                    {"id": "cs_test_payload", "url": "https://checkout.stripe.com/x"},
                    None,
                )
                response = self.client.post(f"/payments/checkout/{course.pk}/")
        return response, create.call_args.kwargs

    def test_course_without_description_omits_the_field(self):
        course = Course.objects.create(
            title="No description", price="10.00", is_published=True,
            description="",
        )
        response, kwargs = self._create_call_kwargs(course)

        self.assertEqual(response.status_code, 302)
        product = kwargs["line_items"][0]["price_data"]["product_data"]
        self.assertEqual(product, {"name": "No description"})
        self.assertNotIn("description", product)

    def test_course_with_description_sends_it(self):
        course = Course.objects.create(
            title="With description", price="10.00", is_published=True,
            description="A short blurb",
        )
        _, kwargs = self._create_call_kwargs(course)

        product = kwargs["line_items"][0]["price_data"]["product_data"]
        self.assertEqual(product["description"], "A short blurb")

    def test_price_is_taken_from_the_database_in_cents(self):
        course = Course.objects.create(
            title="Priced", price="12.34", is_published=True, description="d"
        )
        _, kwargs = self._create_call_kwargs(course)

        price_data = kwargs["line_items"][0]["price_data"]
        self.assertEqual(price_data["unit_amount"], 1234)
        self.assertEqual(price_data["currency"], settings.STRIPE_CURRENCY)
        self.assertEqual(
            kwargs["metadata"],
            {"user_id": str(self.user.pk), "course_id": str(course.pk)},
        )
        self.assertIn(
            "session_id={CHECKOUT_SESSION_ID}", kwargs["success_url"]
        )


class PaymentSuccessPageTests(TestCase):
    """The webhook-free flow: the success page verifies the session with
    Stripe and grants the enrolment itself."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="x"
        )
        cls.other = User.objects.create_user(
            username="someone", email="someone@example.com", password="x"
        )
        cls.course = Course.objects.create(
            title="Paid Course", price="29.00", is_published=True
        )
        cls.other_course = Course.objects.create(
            title="Other Course", price="9.00", is_published=True
        )

    def _session(self, **overrides):
        """A real ``StripeObject``, exactly like the API returns."""
        data = {
            "id": "cs_test_success_1",
            "payment_status": "paid",
            "payment_intent": "pi_test_1",
            "currency": "usd",
            "amount_total": 2900,
            "metadata": {
                "user_id": str(self.user.pk),
                "course_id": str(self.course.pk),
            },
        }
        data.update(overrides)
        return stripe.StripeObject.construct_from(data, None)

    def _success_url(self, course, session_id="cs_test_success_1"):
        return f"/payments/success/{course.pk}/?session_id={session_id}"

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_paid_session_on_success_page_enrolls(self, retrieve):
        retrieve.return_value = self._session()
        self.client.force_login(self.user)

        response = self.client.get(self._success_url(self.course))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment successful")
        self.assertTrue(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())
        payment = Payment.objects.get(stripe_session_id="cs_test_success_1")
        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertEqual(payment.amount, Decimal("29.00"))

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_reloading_success_page_does_not_duplicate(self, retrieve):
        retrieve.return_value = self._session()
        self.client.force_login(self.user)

        self.client.get(self._success_url(self.course))
        self.client.get(self._success_url(self.course))

        self.assertEqual(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_another_users_session_is_refused(self, retrieve):
        retrieve.return_value = self._session(metadata={
            "user_id": str(self.other.pk),
            "course_id": str(self.course.pk),
        })
        self.client.force_login(self.user)

        response = self.client.get(self._success_url(self.course))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirming your payment")
        self.assertFalse(Enrollment.objects.filter(student=self.user).exists())

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_session_for_another_course_is_refused(self, retrieve):
        retrieve.return_value = self._session(metadata={
            "user_id": str(self.user.pk),
            "course_id": str(self.other_course.pk),
        })
        self.client.force_login(self.user)

        self.client.get(self._success_url(self.course))

        self.assertFalse(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_unpaid_session_is_refused(self, retrieve):
        retrieve.return_value = self._session(payment_status="unpaid")
        self.client.force_login(self.user)

        self.client.get(self._success_url(self.course))

        self.assertFalse(Enrollment.objects.filter(
            student=self.user, course=self.course
        ).exists())
        self.assertEqual(Payment.objects.count(), 0)

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    @patch("payments.views.stripe.checkout.Session.retrieve")
    def test_stripe_error_does_not_break_the_page(self, retrieve):
        retrieve.side_effect = stripe.error.StripeError("boom")
        self.client.force_login(self.user)

        response = self.client.get(self._success_url(self.course))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Enrollment.objects.filter(student=self.user).exists())

    def test_success_page_without_session_id_does_not_enroll(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/payments/success/{self.course.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirming your payment")
        self.assertFalse(Enrollment.objects.filter(student=self.user).exists())