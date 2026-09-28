from django.apps import AppConfig
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
