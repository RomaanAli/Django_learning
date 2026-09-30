"""Deployment checks that keep email/OTP misconfiguration visible.

These are registered from ``CoreConfig.ready()`` and therefore run with
``manage.py check`` — which means they also run on every ``manage.py`` command,
including the ``migrate`` step Railway executes at start-up. A *warning* is
used rather than an error so a missing mail provider never blocks a
deployment, but the problem is printed clearly in the deploy log.
"""

import os

from django.conf import settings
from django.core.checks import Warning

# Backend paths used to decide what is actually in use.
FALLBACK_BACKEND = "core.mail_backends.FallbackEmailBackend"
BREVO_BACKEND = "core.mail_backends.BrevoAPIBackend"


def _active_transports():
    """Return the backend paths this environment will really try, in order."""
    if settings.EMAIL_BACKEND == getattr(
        settings, "CHAIN_EMAIL_BACKEND", FALLBACK_BACKEND
    ):
        return list(getattr(settings, "EMAIL_BACKEND_CHAIN", []))
    return [settings.EMAIL_BACKEND]


def _smtp_is_blocked_here():
    """True where outbound SMTP is firewalled (Railway free, Render free)."""
    return bool(
        os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER")
    )


def email_delivery_check(app_configs, **kwargs):
    """Warn when OTP emails cannot actually be delivered.

    Outside development (``EMAIL_DELIVERY_REQUIRED``) the console backend only
    writes emails to the server log. That silently breaks registration: the
    user is told to check their inbox, but nothing is ever sent.
    """
    issues = []
    console_backend = getattr(
        settings,
        "CONSOLE_EMAIL_BACKEND",
        "django.core.mail.backends.console.EmailBackend",
    )
    smtp_backend = getattr(
        settings,
        "SMTP_EMAIL_BACKEND",
        "django.core.mail.backends.smtp.EmailBackend",
    )
    brevo_backend = getattr(settings, "BREVO_EMAIL_BACKEND", BREVO_BACKEND)
    transports = _active_transports()
    real_transports = [
        path for path in transports if path != console_backend
    ]

    # W001 — nothing but the console backend is configured.
    if not real_transports and getattr(
        settings, "EMAIL_DELIVERY_REQUIRED", False
    ):
        issues.append(
            Warning(
                "Email is NOT being delivered: no real email transport is "
                "configured, so OTP emails are only written to this log.",
                hint=(
                    "Set BREVO_API_KEY (Brevo -> \"SMTP & API\" -> \"API "
                    "Keys\"; it starts with xkeysib-) or the SMTP variables "
                    "EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, "
                    "EMAIL_HOST_PASSWORD, EMAIL_USE_TLS and "
                    "DEFAULT_FROM_EMAIL, then redeploy. For Gmail use a "
                    "16-character App Password."
                ),
                id="elearning.W001",
            )
        )

    if settings.EMAIL_BACKEND == smtp_backend and (
        not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD
    ):
        issues.append(
            Warning(
                "The SMTP email backend is active but EMAIL_HOST_USER / "
                "EMAIL_HOST_PASSWORD are empty, so authentication will fail.",
                hint="Add the SMTP credentials to the environment.",
                id="elearning.W002",
            )
        )

    # W003 — the Brevo API is in use but its key is missing.
    if brevo_backend in transports and not getattr(
        settings, "BREVO_API_KEY", ""
    ):
        issues.append(
            Warning(
                "The Brevo email backend is active but BREVO_API_KEY is "
                "empty, so it cannot send anything.",
                hint=(
                    "Generate an API key in Brevo -> \"SMTP & API\" -> \"API "
                    "Keys\", set BREVO_API_KEY, then redeploy."
                ),
                id="elearning.W003",
            )
        )

    # W004 — SMTP-only setup on a host that firewalls outbound SMTP. This is
    # the exact situation that makes OTP emails time out in production.
    if (
        _smtp_is_blocked_here()
        and brevo_backend not in transports
        and smtp_backend in transports
        and getattr(settings, "EMAIL_DELIVERY_REQUIRED", False)
    ):
        issues.append(
            Warning(
                "SMTP is the only configured transport, but this host blocks "
                "outbound SMTP (ports 25/465/587), so OTP emails will time "
                "out instead of being delivered.",
                hint=(
                    "Add BREVO_API_KEY so mail is sent over the Brevo HTTPS "
                    "API on port 443. SMTP is only reachable on Railway Pro "
                    "and on paid Render instances."
                ),
                id="elearning.W004",
            )
        )

    return issues
