"""Stripe Checkout views.

Security model
--------------
* Stripe keys live only in ``settings`` (read from environment variables).
  Nothing secret is ever passed to templates — the publishable key is not even
  needed because we use Stripe's hosted Checkout page (no card data touches
  this server).
* The price is always re-read from ``Course.price`` on the server. The client
  can never set the amount.
* When Stripe sends the student back, the success page asks the Stripe API
  (server-side, secret key) whether that session was really paid — so nobody
  can unlock a course just by visiting the URL. Enrolment is granted in one
  place only: ``fulfill_checkout_session``.
* An optional signature-verified webhook endpoint (``/webhooks/stripe/``)
  calls the very same function, so it can be added later without any code
  changes. It is inert until you create the endpoint in Stripe's dashboard.
"""

from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from courses.models import Course, Enrollment

from .models import Payment

User = get_user_model()


def _price_in_cents(course) -> int:
    """Stripe charges in the smallest currency unit (e.g. cents for USD)."""
    return int(course.price * 100)


def _as_dict(obj):
    """Normalise a StripeObject (or dict) into a plain dict.

    ``stripe.Webhook.construct_event`` returns ``StripeObject`` instances,
    which are NOT dicts (``.get()`` raises ``AttributeError``). Converting to
    a plain dict keeps the webhook handler working with both the real API
    objects and the plain dicts used in tests.
    """
    if isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return dict(obj)


def _redirect_with_message(request, course, level, text):
    messages.add_message(request, level, text)
    return redirect("course_detail", pk=course.pk)


def fulfill_checkout_session(session):
    """Mark the Payment paid and enrol the student — exactly once.

    Accepts either a ``StripeObject`` (what the Stripe API hands back) or a
    plain dict (used in tests); ``_as_dict`` normalises both.

    This single function is the *only* place that grants access, and it is
    called both by the success page (after it asks Stripe whether the session
    was paid) and by the optional webhook. Because
    ``Payment.stripe_session_id`` is unique and ``get_or_create`` is used,
    running it twice for the same session is harmless.
    """
    session = _as_dict(session)

    # For one-time card payments the session is paid as soon as it is
    # completed. Anything else (e.g. async payment methods) arrives with
    # payment_status != paid and must be ignored — only enrol once the money
    # has actually moved.
    if session.get("payment_status") != "paid":
        return False

    session_id = session.get("id")
    metadata = _as_dict(session.get("metadata") or {})
    user_id = metadata.get("user_id")
    course_id = metadata.get("course_id")
    if not session_id or not user_id or not course_id:
        return False

    try:
        user = User.objects.get(pk=user_id)
        course = Course.objects.get(pk=course_id)
    except (User.DoesNotExist, Course.DoesNotExist):
        return False

    amount = course.price
    raw_total = session.get("amount_total")
    if raw_total is not None:
        amount = Decimal(raw_total) / Decimal(100)

    Payment.objects.update_or_create(
        stripe_session_id=session_id,
        defaults={
            "user": user,
            "course": course,
            "amount": amount,
            "currency": session.get("currency") or settings.STRIPE_CURRENCY,
            "stripe_payment_intent": session.get("payment_intent") or "",
            "status": Payment.Status.PAID,
        },
    )
    # Unique constraint on (student, course) + get_or_create = idempotent.
    Enrollment.objects.get_or_create(student=user, course=course)
    return True


class PaymentConfirmView(LoginRequiredMixin, TemplateView):
    """Order summary page shown before the student is sent to Stripe.

    This is the nice-looking "payment page" of the site. The real card form
    lives on Stripe's hosted Checkout page (``session.url``), which keeps this
    project PCI-DSS compliant.
    """

    template_name = "payments/confirm.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(
            Course.objects.filter(is_published=True), pk=self.kwargs["course_id"]
        )
        context["course"] = course
        context["is_enrolled"] = course.enrollments.filter(
            student=self.request.user
        ).exists()
        context["stripe_ready"] = bool(settings.STRIPE_SECRET_KEY)
        return context


class CourseCheckoutView(LoginRequiredMixin, View):
    """Create a Stripe Checkout Session and send the student to Stripe."""

    http_method_names = ["post"]

    def post(self, request, course_id):
        course = get_object_or_404(
            Course.objects.filter(is_published=True), pk=course_id
        )

        if not settings.STRIPE_SECRET_KEY:
            return _redirect_with_message(
                request,
                course,
                messages.ERROR,
                "Payments are not configured yet. Please contact support.",
            )

        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return _redirect_with_message(
                request, course, messages.INFO,
                f'You are already enrolled in "{course.title}".',
            )

        if course.price <= 0:
            # Free course — the plain enroll button is the right path.
            return redirect("enroll_course", pk=course.pk)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        # Never trust a client-supplied price: bill exactly what the course
        # costs in the database.
        # Stripe rejects empty strings for product_data.description, so a course
        # without a description must simply omit the field.
        product_data = {"name": course.title[:250] or f"Course #{course.pk}"}
        if (course.description or "").strip():
            product_data["description"] = course.description.strip()[:250]

        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                client_reference_id=str(request.user.id),
                customer_email=request.user.email or None,
                line_items=[
                    {
                        "price_data": {
                            "currency": settings.STRIPE_CURRENCY,
                            "unit_amount": _price_in_cents(course),
                            "product_data": product_data,
                        },
                        "quantity": 1,
                    }
                ],
                metadata={
                    "user_id": str(request.user.pk),
                    "course_id": str(course.pk),
                },
                success_url=request.build_absolute_uri(
                    reverse("payments:success", args=[course.pk])
                )
                # Stripe replaces this placeholder with the real session id, so
                # the success page can ask Stripe "was this one paid?".
                + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=request.build_absolute_uri(
                    reverse("payments:cancel", args=[course.pk])
                ),
            )
        except stripe.error.StripeError as exc:
            detail = getattr(exc, "user_message", None) or str(exc)
            return _redirect_with_message(
                request, course, messages.ERROR,
                f"The payment could not be started: {detail}",
            )

        # Remember the pending payment so the webhook has the full picture.
        Payment.objects.get_or_create(
            stripe_session_id=session.id,
            defaults={
                "user": request.user,
                "course": course,
                "amount": course.price,
                "currency": settings.STRIPE_CURRENCY,
                "status": Payment.Status.PENDING,
            },
        )
        return redirect(session.url)


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    """Shown right after Stripe redirects the student back (``success_url``).

    No webhook is needed at this stage: Stripe appends ``?session_id=...`` to
    the success URL, so this page asks the Stripe API (server-side, with the
    secret key) whether that exact session was really paid, and only then
    enrols the student. Because the price and the ``user_id``/``course_id``
    come from Stripe's own response and are checked against this request, a
    visitor cannot fake their way into a course by editing the URL.
    """

    template_name = "payments/success.html"

    def _verify_with_stripe(self, course):
        """Ask Stripe about the returned session; True if it really was paid."""
        session_id = self.request.GET.get("session_id")
        if not session_id or not settings.STRIPE_SECRET_KEY:
            return False

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError:
            # Unknown / expired id, network hiccup, ... never crash the page.
            return False

        data = _as_dict(session)
        metadata = _as_dict(data.get("metadata") or {})
        # Only trust a session created for THIS user and THIS course, so an id
        # cannot be replayed for someone else's account or a different course.
        if (
            metadata.get("user_id") != str(self.request.user.pk)
            or metadata.get("course_id") != str(course.pk)
        ):
            return False

        return fulfill_checkout_session(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = get_object_or_404(
            Course.objects.filter(is_published=True), pk=self.kwargs["course_id"]
        )
        enrolled = course.enrollments.filter(student=self.request.user).exists()
        if not enrolled:
            self._verify_with_stripe(course)
            enrolled = course.enrollments.filter(
                student=self.request.user
            ).exists()

        context["course"] = course
        context["is_enrolled"] = enrolled
        return context


class PaymentCancelView(LoginRequiredMixin, TemplateView):
    """The student pressed "Back" / cancelled inside Stripe Checkout."""

    template_name = "payments/cancel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = get_object_or_404(
            Course.objects.filter(is_published=True), pk=self.kwargs["course_id"]
        )
        return context


# --- Webhook ----------------------------------------------------------------


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    """Receives Stripe events (POST with a Stripe-Signature header).

    Endpoint: ``https://<your-domain>/webhooks/stripe/``

    Only ``checkout.session.completed`` is handled. The signature is verified
    with the ``STRIPE_WEBHOOK_SECRET`` endpoint secret; bad signatures get a
    400 so Stripe retries and we can see it in the dashboard.
    """

    def post(self, request):
        payload = request.body
        sig_header = request.headers.get("Stripe-Signature", "")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        if not endpoint_secret:
            return HttpResponseBadRequest("STRIPE_WEBHOOK_SECRET is not configured.")

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            return HttpResponseBadRequest(f"Invalid signature: {exc}")

        if event["type"] == "checkout.session.completed":
            self._handle_session_completed(event["data"]["object"])

        return HttpResponse(status=200)

    @staticmethod
    def _handle_session_completed(session):
        """Kept as a thin wrapper so the webhook and the success page run
        exactly the same fulfilment code (``fulfill_checkout_session``)."""
        return fulfill_checkout_session(session)


stripe_webhook = StripeWebhookView.as_view()