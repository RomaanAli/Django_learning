"""Send one test email through whatever transports are configured.

Usage:

    python manage.py send_test_email you@gmail.com

The command prints which transports are active (masking every secret), then
sends a single message and reports the exact provider error if it fails. It is
the fastest way to prove email delivery works -- locally as well as on a
deployed environment:

    railway run python manage.py send_test_email you@gmail.com
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from core.mail_backends import describe_email_setup

# How many leading characters of a secret are shown when masking it.
MASKED_PREFIX = 10


def _mask(value, shown=MASKED_PREFIX):
    """Return ``value`` shortened to a safe preview, never the full secret."""
    value = value or ""
    if not value:
        return "(not set)"
    return f"{value[:shown]}... (total {len(value)})"


class Command(BaseCommand):
    """Report the active email setup, then send a test message."""

    help = "Send a test email using the configured email backend(s)."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Address to send the test to.")

    def handle(self, *args, **options):
        recipient = options["recipient"]

        # The shared one-liner also warns when EMAIL_BACKEND is pinned by an
        # environment variable (which disables the fallback chain).
        self.stdout.write(describe_email_setup())
        self.stdout.write(
            "BREVO_API_KEY (masked) : "
            f"{_mask(getattr(settings, 'BREVO_API_KEY', ''))}"
        )
        host_port = f"{settings.EMAIL_HOST}:{settings.EMAIL_PORT}"
        self.stdout.write(f"EMAIL_HOST             : {host_port}")
        self.stdout.write(
            "SMTP user (masked)     : "
            f"{_mask(settings.EMAIL_HOST_USER, shown=3)}"
        )
        self.stdout.write(
            "Delivery required      : "
            f"{getattr(settings, 'EMAIL_DELIVERY_REQUIRED', False)}"
        )
        self.stdout.write("")

        try:
            sent = send_mail(
                "E-Learning test email",
                "If you can read this, email delivery works.",
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001 - surface the real reason
            raise CommandError(
                f"Could not send the test email: {type(exc).__name__}: {exc}"
            ) from exc

        if not sent:
            raise CommandError(
                "No transport reported success (see the details above)."
            )
        self.stdout.write(
            self.style.SUCCESS(f"Test email sent to {recipient}.")
        )
