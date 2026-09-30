from django.apps import AppConfig
from django.conf import settings
from django.core.checks import register


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """Register the project's deployment checks (email/OTP configuration).

        ``registered_checks`` is a set, so registering here is idempotent even
        if the module is imported again.
        """
        from . import checks

        register(checks.email_delivery_check)
        self._log_email_setup()

    @staticmethod
    def _log_email_setup():
        """Print the active email transports into the deploy log.

        Only when this environment must really deliver mail: on a cloud host a
        silent "the OTP never arrived" is very hard to debug, so state the
        truth at start-up instead. Never prints any secret.
        """
        if not getattr(settings, "EMAIL_DELIVERY_REQUIRED", False):
            return

        from .mail_backends import describe_email_setup

        print(describe_email_setup(), flush=True)
