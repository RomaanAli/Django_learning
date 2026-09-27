import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from allauth.socialaccount.adapter import get_adapter

from .forms import ProfileForm, StudentRegistrationForm, UserEditForm
from .models import EmailVerification, Profile

# --- Email OTP configuration -------------------------------------------------
OTP_LIFETIME_MINUTES = 5       # how long an OTP stays valid
RESEND_COOLDOWN_SECONDS = 60   # minimum wait between OTP resends


# --- Email OTP helpers -------------------------------------------------------


def _generate_otp() -> str:
    """Return a cryptographically random 6-digit code (may start with 0)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _send_otp_email(user, otp: str) -> bool:
    """Email the OTP to the user; return True on success.

    Development: the console backend prints the whole email (OTP included) to
    the runserver terminal instead of sending it.
    Production: the SMTP backend really sends it using the EMAIL_* variables.

    On failure the error is printed to the server console (so it is easy to
    see in the terminal) and False is returned so the views can say so.
    """
    subject = "Verify Your E-Learning Account"
    message = (
        f"Hi {user.username},\n\n"
        f"Your verification OTP is:\n\n{otp}\n\n"
        f"This OTP will expire in {OTP_LIFETIME_MINUTES} minutes.\n\n"
        "If you did not request this account, you can ignore this email."
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception as exc:
        print(f"[email] Could not send OTP to {user.email}: {exc}", flush=True)
        return False
    return True


def _create_or_refresh_otp(user) -> str:
    """Create (or replace) the user's OTP, store it, and return it.

    A single row per user means a resend simply overwrites the old code,
    so the previous OTP stops working immediately.
    """
    now = timezone.now()
    otp = _generate_otp()
    EmailVerification.objects.update_or_create(
        user=user,
        defaults={
            "otp": otp,
            "created_at": now,
            "expires_at": now + timedelta(minutes=OTP_LIFETIME_MINUTES),
            "is_verified": False,
        },
    )
    return otp


def _is_email_verified(user) -> bool:
    """True when the user has a verification record marked as verified."""
    try:
        return user.email_verification.is_verified
    except EmailVerification.DoesNotExist:
        return False


def _set_pending_user(request, user) -> None:
    """Remember which account is being verified in this browser session."""
    request.session["pending_user_id"] = user.id


def _is_google_configured(request) -> bool:
    """True when Google OAuth credentials are available.

    Mirrors allauth's own lookup: settings-backed apps (from the
    GOOGLE_OAUTH_CLIENT_* environment variables) or a SocialApp record
    in the database for the current site.
    """
    try:
        return bool(get_adapter(request).list_apps(request, provider="google"))
    except Exception:
        return False


# --- Views -------------------------------------------------------------------


class RegisterView(View):
    """Let a new student create an account (activated by email OTP)."""

    template_name = "accounts/register.html"

    def _render(self, request, form):
        return render(
            request,
            self.template_name,
            {"form": form, "google_configured": _is_google_configured(request)},
        )

    def get(self, request):
        return self._render(request, StudentRegistrationForm())

    def post(self, request):
        form = StudentRegistrationForm(request.POST)
        if not form.is_valid():
            return self._render(request, form)

        user = form.save()  # created with is_active=False
        otp = _create_or_refresh_otp(user)
        if not _send_otp_email(user, otp):
            # Email failed (SMTP not configured / misconfigured). Remove the
            # half-registered account so the user can retry cleanly, and say
            # what happened instead of silently leaving them stuck.
            user.delete()
            messages.error(
                request,
                "We could not send the verification email (details in the "
                "server console). Please check the EMAIL_* settings and try again.",
            )
            return redirect("register")
        _set_pending_user(request, user)
        messages.info(
            request,
            "Almost done! Check your email for a 6-digit code to activate your account.",
        )
        return redirect("verify_email")


class LoginView(View):
    """Log a student in, redirecting unverified users to the OTP page."""

    template_name = "accounts/login.html"

    def _render(self, request, form):
        return render(
            request,
            self.template_name,
            {"form": form, "google_configured": _is_google_configured(request)},
        )

    def get(self, request):
        return self._render(request, AuthenticationForm())

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                request.session.pop("pending_user_id", None)
                login(request, user)
                next_url = request.POST.get("next")
                if not next_url or not url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_url = "dashboard"
                return redirect(next_url)
        else:
            # Django's auth backend silently refuses INACTIVE accounts, so an
            # unverified user would normally just see "invalid username or
            # password". Detect correct credentials on an unverified account
            # instead, and send the user to the OTP verification page.
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = User.objects.filter(username=username).first() if username else None
            if (
                user is not None
                and password
                and not user.is_active
                and user.check_password(password)
                and not _is_email_verified(user)
            ):
                _set_pending_user(request, user)
                messages.info(request, "Please verify your email before logging in.")
                return redirect("verify_email")
        return self._render(request, form)



class VerifyEmailView(View):
    """OTP page: activate the account when the entered code matches."""

    template_name = "accounts/verify_otp.html"

    def _pending_user(self, request):
        """Return the pending user, or None after telling them to register."""
        user_id = request.session.get("pending_user_id")
        if not user_id:
            messages.info(request, "No pending registration found. Please register first.")
            return None
        user = User.objects.filter(id=user_id).first()
        if user is None:
            request.session.pop("pending_user_id", None)
            messages.info(request, "No pending registration found. Please register first.")
            return None
        return user

    def _verify_and_redirect(self, request, user):
        """If the email is already verified take the user to login."""
        if _is_email_verified(user):
            user.is_active = True
            user.save(update_fields=["is_active"])
            request.session.pop("pending_user_id", None)
            messages.success(request, "Email verified successfully. You can now log in.")
            return redirect("login")
        return None

    def get(self, request):
        user = self._pending_user(request)
        if user is None:
            return redirect("register")

        redirected = self._verify_and_redirect(request, user)
        if redirected is not None:
            return redirected

        return render(request, self.template_name, {"user": user})

    def post(self, request):
        user = self._pending_user(request)
        if user is None:
            return redirect("register")

        redirected = self._verify_and_redirect(request, user)
        if redirected is not None:
            return redirected

        entered = request.POST.get("otp", "").strip()
        verification = EmailVerification.objects.filter(user=user).first()

        if verification is None:
            # No code on file (edge case) — issue a fresh one.
            otp = _create_or_refresh_otp(user)
            if _send_otp_email(user, otp):
                messages.info(request, "A new OTP has been emailed to you.")
            else:
                messages.error(
                    request,
                    "We could not send the verification email (details in the "
                    "server console). Please check the EMAIL_* settings and try again.",
                )
            return redirect("verify_email")
        if not entered:
            messages.error(request, "Please enter the OTP.")
        elif verification.is_expired:
            messages.error(request, "OTP has expired. Please request a new OTP.")
        elif not secrets.compare_digest(entered, verification.otp):
            messages.error(request, "Invalid OTP.")
        else:
            # Correct code: activate the account and burn the OTP.
            user.is_active = True
            user.save(update_fields=["is_active"])
            verification.is_verified = True
            verification.otp = ""
            verification.save(update_fields=["is_verified", "otp"])
            request.session.pop("pending_user_id", None)
            messages.success(request, "Email verified successfully. You can now log in.")
            return redirect("login")

        return render(request, self.template_name, {"user": user})


class ResendOtpView(View):
    """Send a fresh OTP (invalidates the old one) with a 60s cooldown."""

    def _resend(self, request):
        user_id = request.session.get("pending_user_id")
        if not user_id:
            messages.info(request, "No pending registration found. Please register first.")
            return redirect("register")

        user = User.objects.filter(id=user_id).first()
        if user is None:
            request.session.pop("pending_user_id", None)
            messages.info(request, "No pending registration found. Please register first.")
            return redirect("register")

        if _is_email_verified(user):
            request.session.pop("pending_user_id", None)
            messages.success(request, "Your email is already verified. You can log in.")
            return redirect("login")

        verification = EmailVerification.objects.filter(user=user).first()
        if verification is not None:
            wait_left = RESEND_COOLDOWN_SECONDS - (
                timezone.now() - verification.created_at
            ).total_seconds()
            if wait_left > 0:
                messages.error(
                    request,
                    f"Please wait {int(wait_left) + 1} seconds before requesting a new OTP.",
                )
                return redirect("verify_email")

        sent = _send_otp_email(user, _create_or_refresh_otp(user))
        if not sent:
            messages.error(
                request,
                "We could not send the verification email (details in the server "
                "console). Please check the EMAIL_* settings and try again.",
            )
            return redirect("verify_email")
        messages.success(request, "A new OTP has been sent to your email.")
        return redirect("verify_email")

    def get(self, request):
        # The original FBV did not restrict the HTTP method; keep GET working.
        return self._resend(request)

    def post(self, request):
        return self._resend(request)


class LogoutView(View):
    """Log the user out — but only on the confirmed POST from the modal.

    A plain link (GET request) can never silently end a session; it just
    shows a friendly message and takes the user to the home page instead.
    """

    def get(self, request):
        messages.info(
            request,
            "You were not logged out. Use the Logout button and confirm to end "
            "your session.",
        )
        return redirect("home")

    def post(self, request):
        logout(request)
        return redirect("home")



class DashboardView(LoginRequiredMixin, TemplateView):
    """Show the logged-in student's dashboard and enrollments."""

    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["enrollments"] = (
            self.request.user.enrollments.select_related("course").all()
        )
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    """Show the logged-in student's profile page."""

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context["profile"] = profile
        return context


class ProfileEditView(LoginRequiredMixin, View):
    """Edit the logged-in student's profile (name, email, age, contact)."""

    template_name = "accounts/profile_edit.html"

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )

    def post(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )

