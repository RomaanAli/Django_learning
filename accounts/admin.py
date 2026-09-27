from django.contrib import admin

from .models import EmailVerification, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "age", "contact")
    search_fields = ("user__username", "user__email")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "is_verified", "created_at", "expires_at")
    list_filter = ("is_verified",)
    readonly_fields = ("otp", "created_at", "expires_at")
