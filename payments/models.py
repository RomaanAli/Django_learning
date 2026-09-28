from django.conf import settings
from django.db import models


class Payment(models.Model):
    """One Stripe Checkout Session per course purchase.

    ``stripe_session_id`` is unique so the webhook can never enroll a student
    twice for the same payment (idempotency), even if Stripe retries the event.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    stripe_session_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Stripe Checkout Session id (used for webhook idempotency).",
    )
    stripe_payment_intent = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe PaymentIntent id, filled in by the webhook.",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount actually charged, in STRIPE_CURRENCY units.",
    )
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.course.title} - {self.get_status_display()}"