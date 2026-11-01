from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import EmailVerification, InstructorDocument, Profile, User


class CustomUserChangeForm(UserChangeForm):
    """Re-binds Django's change form to the project's custom user."""

    class Meta(UserChangeForm.Meta):
        model = User


class CustomUserCreationForm(UserCreationForm):
    """Re-binds Django's add-user form to the project's custom user."""

    class Meta(UserCreationForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin UI for the custom user (standard UserAdmin features)."""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = ("username", "email", "role", "is_approved_instructor", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_approved_instructor", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("role", "is_approved_instructor", "email", "username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("role", "email", "username", "password1", "password2"),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "age", "contact")
    search_fields = ("user__username", "user__email")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "is_verified", "created_at", "expires_at")
    list_filter = ("is_verified",)
    readonly_fields = ("otp", "created_at", "expires_at")


@admin.register(InstructorDocument)
class InstructorDocumentAdmin(admin.ModelAdmin):
    """Admin UI for instructor document uploads and approval."""

    list_display = (
        "user",
        "get_user_role",
        "status",
        "created_at",
        "approved_by",
        "get_is_approved_instructor",
    )
    list_filter = ("status",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "approved_at", "approved_by")
    autocomplete_fields = ("user", "approved_by")
    fieldsets = (
        (None, {"fields": ("user", "file", "status", "review_note")}),
        ("Approval", {"fields": ("approved_by", "approved_at")}),
    )

    @admin.display(description="Role", ordering="user__role")
    def get_user_role(self, obj):
        return obj.user.get_role_display() if obj.user else "-"

    @admin.display(description="Can teach", boolean=True, ordering="user__is_approved_instructor")
    def get_is_approved_instructor(self, obj):
        return obj.user.is_approved_instructor if obj.user else False

    def save_model(self, request, obj, form, change):
        """Apply the approval decision to the document and its owner.

        The heavy lifting lives in ``InstructorDocument.approve``/``deny`` so
        the admin, a management command and the shell all agree on what
        "approved" means. This method only supplies the reviewer.
        """
        if obj.status == InstructorDocument.STATUS_APPROVED and obj.user_id == request.user.pk:
            from django.contrib import messages
            messages.error(
                request,
                "Self-approval is forbidden: an admin cannot approve their own instructor document."
            )
            if not obj.user.is_approved_instructor:
                obj.status = InstructorDocument.STATUS_PENDING
            super().save_model(request, obj, form, change)
            return

        super().save_model(request, obj, form, change)

        if obj.status == InstructorDocument.STATUS_APPROVED:
            obj.approve(reviewer=request.user)
        elif obj.status == InstructorDocument.STATUS_DENIED:
            reason = (obj.review_note or "").strip() or "Application requirements not met."
            obj.deny(reviewer=request.user, reason=reason)

    def get_readonly_fields(self, request, obj=None):
        """Once approved the reviewer/timestamp are fixed by the system."""
        if obj is not None and obj.approved_at and obj.status == InstructorDocument.STATUS_APPROVED:
            return tuple(self.readonly_fields)
        return self.readonly_fields

