from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "course__title",
        "stripe_session_id",
    )
    readonly_fields = ("created_at", "updated_at")