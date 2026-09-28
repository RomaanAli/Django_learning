"""Deployment checks that keep email/OTP misconfiguration visible.

These are registered from ``CoreConfig.ready()`` and therefore run with
``manage.py check`` — which means they also run on every ``manage.py`` command,
including the ``migrate`` step Railway executes at start-up. A *warning* is
used rather than an error so a missing mail provider never blocks a
deployment, but the problem is printed clearly in the deploy log.
"""

from django.conf import settings
from django.core.checks import Warning


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

    if settings.EMAIL_BACKEND == console_backend and getattr(
        settings, "EMAIL_DELIVERY_REQUIRED", False
    ):
        issues.append(
            Warning(
                "Email is NOT being delivered: the console email backend is "
                "active even though this environment is expected to send real "
                "mail. OTP emails are only written to this log.",
                hint=(
                    "Set EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, "
                    "EMAIL_HOST_PASSWORD, EMAIL_USE_TLS and DEFAULT_FROM_EMAIL "
                    "in the environment (and remove any EMAIL_BACKEND override), "
                    "then redeploy. For Gmail use a 16-character App Password."
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

    return issues
