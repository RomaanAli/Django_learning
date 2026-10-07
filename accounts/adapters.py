"""Custom django-allauth adapters.

The only Override is for social accounts: the Google OAuth client can end up
configured twice at the same time — once as a SocialApp row in the Django
admin (``/admin/socialaccount/socialapp/``) and once through the
``GOOGLE_OAUTH_CLIENT_*`` environment variables that ``E_learning/settings.py``
reads into ``SOCIALACCOUNT_PROVIDERS["google"]["APP"]``.

allauth's default ``get_app()`` raises ``MultipleObjectsReturned`` in that
situation, which surfaces to the visitor as a 500 "Internal Server Error" the
moment they click "Continue with Google".  We flatten duplicates that share
the same ``client_id`` (they are the same OAuth client, just registered
twice) and, when genuinely different clients are configured, prefer the
settings-backed app — the deployment configuration — over database rows.
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Default behaviour, except that the Google / any provider app lookup no
    longer fails when the same OAuth app is registered in more than one place.
    """

    def get_app(self, request, provider, client_id=None):
        """Return one app for ``provider`` without tripping over duplicates.

        Logic compared to the default implementation:

        * No apps at all -> ``SocialApp.DoesNotExist`` (unchanged).
        * Several apps that are really the same OAuth client (same
          ``client_id``, e.g. a Django-admin SocialApp row *and* the
          ``GOOGLE_OAUTH_CLIENT_*`` env-var config) -> the first one wins
          instead of a 500 ``MultipleObjectsReturned``.
        * Several apps with *distinct* ``client_id`` values -> the
          settings-backed app (the one built from
          ``SOCIALACCOUNT_PROVIDERS``, i.e. environment variables) is
          preferred, because that is the documented way this project is
          configured; otherwise the first database app wins.
        """
        apps = self.list_apps(request, provider=provider, client_id=client_id)
        if not apps:
            raise SocialApp.DoesNotExist()

        unique_by_client = {app.client_id: app for app in apps}
        if len(unique_by_client) == 1:
            return next(iter(unique_by_client.values()))

        settings_backed = [app for app in apps if app.pk is None]
        if settings_backed:
            return settings_backed[0]

        return apps[0]