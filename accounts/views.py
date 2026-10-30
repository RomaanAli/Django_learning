import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from allauth.socialaccount.adapter import get_adapter

from .forms import (
    InstructorDocumentForm,
    ProfileForm,
    StudentRegistrationForm,
    UserEditForm,
    VALID_REGISTER_ROLES,
)
from allauth.account.models import EmailAddress

from .models import EmailVerification, InstructorDocument, Profile
from .permissions import InstructorRequiredMixin

from courses.models import Course

User = get_user_model()

OTP_LIFETIME_MINUTES = 5
RESEND_COOLDOWN_SECONDS = 60




def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _send_otp_email(user, otp: str, request=None) -> bool:

    subject = "Verify Your E-Learning Account"
    context = {
        "user": user,
        "username": user.username,
        "otp": otp,
        "otp_lifetime_minutes": OTP_LIFETIME_MINUTES,
    }
    message = render_to_string("accounts/emails/otp_email.txt", context)
    html_message = render_to_string("accounts/emails/otp_email.html", context)
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
        )
    except Exception as exc:
        print(f"[email] Could not send OTP to {user.email}: {exc}", flush=True)
        return False
    return True


def _create_or_refresh_otp(user) -> str:

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

    try:
        return user.email_verification.is_verified
    except EmailVerification.DoesNotExist:
        return False


def _set_pending_user(request, user) -> None:

    request.session["pending_user_id"] = user.id


def _activate_user(request, user) -> None:
    """Activate a user after OTP verification, applying the role stored
    server-side during registration (validated against the allowlist)."""
    pending_role = request.session.get("pending_user_role")
    if pending_role not in (User.ROLE_STUDENT, User.ROLE_INSTRUCTOR):
        pending_role = getattr(user, "role", User.ROLE_STUDENT)
    if pending_role not in (User.ROLE_STUDENT, User.ROLE_INSTRUCTOR):
        pending_role = User.ROLE_STUDENT
    user.role = pending_role
    user.is_active = True
    user.save(update_fields=["role", "is_active"])
    request.session.pop("pending_user_id", None)
    request.session.pop("pending_user_role", None)


def _is_google_configured(request) -> bool:

    try:
        return bool(get_adapter(request).list_apps(request, provider="google"))
    except Exception:
        return False

class RegisterView(View):

    template_name = "accounts/register.html"

    def _selected_role(self, value):
        value = (value or "").strip().lower()
        if value not in dict(VALID_REGISTER_ROLES):
            value = User.ROLE_STUDENT
        return value

    def _render(self, request, form, selected_role="student"):
        selected_role = self._selected_role(selected_role)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "google_configured": _is_google_configured(request),
                "selected_role": selected_role,
            },
        )

    def get(self, request):
        role = self._selected_role(request.GET.get("role"))
        form = StudentRegistrationForm(initial={"role": role})
        return self._render(request, form, selected_role=role)

    def post(self, request):
        email = (request.POST.get("email") or "").strip()
        if email:
            stale_ids = [
                u.pk
                for u in User.objects.filter(email__iexact=email)
                if not u.is_active and not _is_email_verified(u)
            ]
            if stale_ids:
                User.objects.filter(pk__in=stale_ids).delete()

        submitted_role = self._selected_role(request.POST.get("role"))
        form = StudentRegistrationForm(request.POST)
        if not form.is_valid():
            return self._render(request, form, selected_role=submitted_role)

        user = form.save()
        request.session["pending_user_role"] = (
            user.role
            if user.role in (User.ROLE_STUDENT, User.ROLE_INSTRUCTOR)
            else User.ROLE_STUDENT
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=False,
        )
        try:
            otp = _create_or_refresh_otp(user)
        except Exception as e:
            print("otp generation failed:", e)
            user.delete()
            messages.error(
                request,
                "We could not prepare email verification (details in the "
                "server console). Please try again.",
            )
            return redirect("register")

        if not _send_otp_email(user, otp):
            user.delete()
            messages.error(
                request,
                "We could not send the verification email (the reason is "
                "printed in the server log). Please check BREVO_API_KEY and "
                "the EMAIL_* settings, then try again.",
            )
            return redirect("register")
        _set_pending_user(request, user)
        messages.info(
            request,
            "Almost done! Check your email for a 6-digit code to activate your account.",
        )
        return redirect("verify_email")


class LoginView(View):

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
                request.session.pop("pending_user_role", None)
                login(request, user)
                next_url = request.POST.get("next") or request.GET.get("next")
                if user.is_instructor or user.is_admin:
                    if not next_url or not url_has_allowed_host_and_scheme(
                        next_url,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    ):
                        next_url = "instructor_dashboard"
                    return redirect(next_url)
                if not next_url or not url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_url = "dashboard"
                return redirect(next_url)
        else:
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = None
            if username:
                user = User.objects.filter(username=username).first()
                if user is None:
                    user = (
                        User.objects.filter(email__iexact=username).first()
                        if "@" in username
                        else None
                    )
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

    template_name = "accounts/verify_otp.html"

    def _pending_user(self, request):

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

        if _is_email_verified(user):
            _activate_user(request, user)
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
            _activate_user(request, user)
            verification.is_verified = True
            verification.otp = ""
            verification.save(update_fields=["is_verified", "otp"])
            messages.success(request, "Email verified successfully. You can now log in.")
            return redirect("login")

        return render(request, self.template_name, {"user": user})


class ResendOtpView(View):

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
        return self._resend(request)

    def post(self, request):
        return self._resend(request)


class LogoutView(View):

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

    template_name = "accounts/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        # The student dashboard is for students only; instructors/admins
        # have their own dashboard and were previously shown an empty
        # student page here.
        if request.user.is_authenticated and not request.user.is_student:
            return redirect("instructor_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.db.models import Count, Prefetch

        context = super().get_context_data(**kwargs)
        # Annotate the prefetched course so the template can use
        # enrollment.course.lesson_count instead of .lessons.count()
        # (one query per row); template now uses the annotated field.
        context["enrollments"] = (
            self.request.user.enrollments.prefetch_related(
                Prefetch(
                    "course",
                    queryset=Course.objects.annotate(
                        lesson_count=Count("lessons", distinct=True),
                        enrollment_count=Count(
                            "enrollments", distinct=True
                        ),
                    ),
                )
            ).all()
        )
        return context


class ProfileView(LoginRequiredMixin, TemplateView):

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context["profile"] = profile
        return context


def google_check(request):
    # Diagnostics page: previously public to anyone, leaking settings,
    # host/site details and masked OAuth client ids. Staff/superuser only.
    from django.http import HttpResponseForbidden

    if not request.user.is_authenticated or not (
        request.user.is_staff or request.user.is_superuser
    ):
        return HttpResponseForbidden(
            "Google login diagnostics are available to staff only."
        )

    import os as _os
    from allauth.socialaccount.adapter import get_adapter
    from django.contrib.sites.shortcuts import get_current_site
    from django.http import HttpResponse
    from django.urls import reverse

    def mask(value, shown=10):
        value = value or ""
        if not value:
            return "(not set)"
        return f"{value[:shown]}... (total {len(value)})"

    items = []

    def add(name, value):
        items.append((name, str(value)))

    add("request URL", request.build_absolute_uri())
    add("scheme", request.scheme)
    add("host", request.get_host())
    add("DEBUG", settings.DEBUG)
    add("ALLOWED_HOSTS", settings.ALLOWED_HOSTS)
    add("CSRF_TRUSTED_ORIGINS", settings.CSRF_TRUSTED_ORIGINS)
    add("SITE_ID", getattr(settings, "SITE_ID", None))
    try:
        add("current Site domain", get_current_site(request).domain)
    except Exception as exc:
        add("current Site domain", f"ERROR {type(exc).__name__}: {exc}")

    add(
        "GOOGLE_OAUTH_CLIENT_ID",
        mask(_os.environ.get("GOOGLE_OAUTH_CLIENT_ID")),
    )
    secret = _os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or ""
    add(
        "GOOGLE_OAUTH_CLIENT_SECRET",
        f"{'yes' if secret else 'no'} (len {len(secret)})",
    )

    try:
        apps = get_adapter(request).list_apps(request, provider="google")
        for i, app in enumerate(apps, 1):
            add(
                f"google app #{i}",
                f"pk={app.pk} name={app.name!r} "
                f"provider={app.provider} client_id={mask(app.client_id)}",
            )
        add("total google apps allauth sees", len(apps))
    except Exception as exc:
        add("list_apps", f"ERROR {type(exc).__name__}: {exc}")

    redirect_uris = []
    try:
        callback_path = reverse("google_callback")

        redirect_uris.append(request.build_absolute_uri(callback_path))
        host = request.get_host()
        hostname = host.split(":")[0]
        port = host[len(hostname):]
        alternate = None
        if hostname == "localhost":
            alternate = "127.0.0.1" + port
        elif hostname == "127.0.0.1":
            alternate = "localhost" + port
        if alternate:
            redirect_uris.append(f"{request.scheme}://{alternate}{callback_path}")
        add(
            "redirect_uri allauth sends to Google (register it VERBATIM)",
            redirect_uris[0],
        )
        for uri in redirect_uris[1:]:
            add("alternate loopback redirect_uri (register it too)", uri)
    except Exception as exc:
        add("callback URL", f"ERROR {type(exc).__name__}: {exc}")

    from django.utils.html import escape

    rows = "".join(
        f"<tr><td>{escape(k)}</td><td class='v'>{escape(v)}</td></tr>"
        for k, v in items
    )

    uris_html = "".join(f"<li><code>{escape(u)}</code></li>" for u in redirect_uris)
    checklist = [
        "<b>1. Register the redirect URIs.</b> Google Cloud Console &rarr; "
        "APIs &amp; Services &rarr; <b>Credentials</b> &rarr; OAuth 2.0 "
        "Client ID (type <i>Web application</i>) &rarr; <b>Authorized "
        "redirect URIs</b> &rarr; paste each of these <i>exactly</i> "
        "(scheme, port and trailing slash all matter) &rarr; <b>Save</b> "
        "&rarr; wait ~1 minute before retrying:<ul>"
        + uris_html
        + "</ul>Google error <i>400: redirect_uri_mismatch</i> means this "
        "list is wrong for the host you are browsing with.",
        "<b>2. Allow the account you sign in with.</b> APIs &amp; Services "
        "&rarr; <b>OAuth consent screen</b> &rarr; while <i>Publishing "
        "status</i> is <i>Testing</i>, add your Google account under "
        "<b>Test users</b> &rarr; <b>Save</b> (or click <b>Publish app</b> "
        "so every account works). The <i>Access blocked / 403</i> error for "
        "one specific account means that account is missing from this list.",
        "<b>3. Use matching credentials.</b> The client id / secret in "
        "<code>.env</code> (or the SocialApp row in Django admin) must "
        "belong to that same <i>Web application</i> client — a client of "
        "any other type (Android, TVs, etc.) cannot complete this flow.",
        "<b>4. Keep the host consistent.</b> If only "
        "<code>localhost</code> is registered, browse "
        "<code>http://localhost:&lt;port&gt;/</code> — not "
        "<code>127.0.0.1</code> (and vice versa); the redirect_uri "
        "changes with the host name.",
    ]
    checklist_html = "".join(f"<li>{c}</li>" for c in checklist)

    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Google login "
        "diagnostics</title><style>body{font-family:monospace;max-width:1100px;"
        "margin:24px auto;padding:0 16px}table{border-collapse:collapse;"
        "width:100%}td{border:1px solid #999;padding:6px 12px;vertical-align:"
        "top;word-break:break-all}td.v{max-width:900px}h2{margin-top:32px}"
        "code{background:#f3f3f3;padding:2px 4px}li{margin:8px 0}</style>"
        "</head><body><h1>Google login diagnostics</h1>"
        f"<table>{rows}</table>"
        "<h2>Fixing Google's &quot;Access blocked&quot; page</h2>"
        "<p>That error is generated by Google's servers after the redirect "
        "to <code>accounts.google.com</code>, so it is fixed in the Google "
        "Cloud Console, not in Django. Work through this list:</p>"
        f"<ol>{checklist_html}</ol>"
        "</body></html>"
    )
    return HttpResponse(html, content_type="text/html; charset=utf-8")


class ProfileEditView(LoginRequiredMixin, View):

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


class InstructorApplyView(LoginRequiredMixin, View):
    """Let a logged-in learner apply to become an instructor.

    Applying uploads one document (a certificate, ID or similar). The upload
    is stored as ``pending``; an admin approves it from the Django admin,
    which promotes the user to the ``instructor`` role.
    """

    template_name = "accounts/instructor_apply.html"

    def _document(self, user):
        return InstructorDocument.objects.filter(user=user).first()

    def get(self, request):
        if request.user.is_instructor:
            messages.info(request, "You are already an instructor.")
            return redirect("instructor_dashboard")

        document = self._document(request.user)
        form = InstructorDocumentForm(
            instance=document,
            initial={"file": document.file if document else None},
        )
        return render(
            request,
            self.template_name,
            {"form": form, "document": document},
        )

    def post(self, request):
        if request.user.is_instructor:
            messages.info(request, "You are already an instructor.")
            return redirect("instructor_dashboard")

        document = self._document(request.user)
        form = InstructorDocumentForm(request.POST, request.FILES, instance=document)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "document": document},
            )

        document = form.save(commit=False)
        document.user = request.user
        document.status = InstructorDocument.STATUS_PENDING
        document.approved_at = None
        document.approved_by = None
        document.save()

        messages.success(
            request,
            "Thanks! Your document was uploaded and is waiting for approval.",
        )
        return redirect("instructor_apply")


class InstructorDashboardView(InstructorRequiredMixin, TemplateView):
    """Landing page for instructors: their courses and student counts."""

    template_name = "accounts/instructor_dashboard.html"

    def get_context_data(self, **kwargs):
        from django.db.models import Count

        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Mirror InstructorCourseListView: admins see all courses, not
        # just the (usually empty) set they personally teach.
        if user.is_admin or user.is_superuser:
            qs = Course.objects.all()
        else:
            qs = user.courses_taught.all()
        courses = list(
            qs.select_related("instructor").annotate(
                lesson_count=Count("lessons", distinct=True),
                enrollment_count=Count("enrollments", distinct=True),
            )
        )
        context["courses"] = courses
        context["student_count"] = sum(
            course.enrollment_count for course in courses
        )
        context["draft_courses"] = [c for c in courses if not c.is_published]
        return context


