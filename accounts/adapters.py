from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to redirect instructors to their dashboard."""

    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            if request.user.is_instructor or request.user.is_admin:
                return reverse("instructor_dashboard")
        return super().get_login_redirect_url(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Default behaviour with duplicate app handling, role preservation on login,
    and automatic student default (or selected instructor role) for new social signups.
    """

    def get_app(self, request, provider, client_id=None):
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

    def pre_social_login(self, request, sociallogin):
        # IF the social login belongs to an EXISTING user:
        # DO NOTHING to role, is_approved_instructor, is_active, or email.
        # Return / log in unchanged.
        if sociallogin.is_existing:
            return

        User = get_user_model()

        # Connect to existing user with matching email if present
        email = getattr(sociallogin.user, "email", None)
        if email:
            existing = User.objects.filter(email__iexact=email).first()
            if existing:
                sociallogin.connect(request, existing)
                return

        # NEW user signup via Google:
        # Read the role if selected on the register page, otherwise default to Student.
        role = request.session.pop("pending_signup_role", None)
        if role not in (User.ROLE_STUDENT, User.ROLE_INSTRUCTOR):
            role = User.ROLE_STUDENT

        request.session["_google_new_user_role"] = role

    def save_user(self, request, sociallogin, form=None):
        User = get_user_model()
        u = sociallogin.user
        role = request.session.pop("_google_new_user_role", None) or User.ROLE_STUDENT
        if role not in (User.ROLE_STUDENT, User.ROLE_INSTRUCTOR):
            role = User.ROLE_STUDENT

        u.role = role
        u.is_approved_instructor = False
        u.is_active = True
        u.set_unusable_password()
        super().save_user(request, sociallogin, form=form)
        return u
