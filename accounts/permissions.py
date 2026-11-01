"""Role-based access control helpers.

The project gives every user a ``role`` (``student`` / ``instructor`` /
``admin``). These mixins turn that field into an actual permission check for
class-based views, so a view can declare who is allowed in and everybody else
is redirected to the login page (or to a "not allowed" page).

They are deliberately thin wrappers around Django's ``AccessMixin`` so they
behave exactly like ``LoginRequiredMixin`` — same redirects, same
``raise_exception`` behaviour.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):

    allowed_roles = ()

    def get_allowed_roles(self):
        return tuple(self.allowed_roles)

    def has_permission(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # Inactive (e.g. unverified) accounts must not pass a role check
        # even via force-login style sessions. No existing test relies on
        # an inactive user passing (checked: all force_login users in the
        # test suite are active).
        if not user.is_active:
            return False
        if user.is_superuser:
            return True
        return user.role in self.get_allowed_roles()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(
            "Your account does not have permission to view this page."
        )


class InstructorRequiredMixin(RoleRequiredMixin):
    """Allow instructors and admins only."""

    allowed_roles = ("instructor", "admin")


class ApprovedInstructorRequiredMixin(InstructorRequiredMixin):
    """Allow approved instructors and admins only (can_teach is True).

    Pending and denied instructors are redirected to the instructor dashboard
    status page with an informative message.
    """

    def has_permission(self):
        user = self.request.user
        if not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        return user.can_teach

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        from django.contrib import messages
        from django.shortcuts import redirect
        if self.request.user.is_instructor:
            messages.info(
                self.request,
                "Your instructor account is pending admin approval before you can manage courses."
            )
            return redirect("instructor_dashboard")
        raise PermissionDenied("Your account does not have permission to view this page.")


class AdminRequiredMixin(RoleRequiredMixin):
    """Allow admins only (plus Django superusers)."""

    allowed_roles = ("admin",)


class StudentRequiredMixin(RoleRequiredMixin):
    """Allow students only."""

    allowed_roles = ("student",)
