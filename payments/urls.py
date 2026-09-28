from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "confirm/<int:course_id>/",
        views.PaymentConfirmView.as_view(),
        name="confirm",
    ),
    path(
        "checkout/<int:course_id>/",
        views.CourseCheckoutView.as_view(),
        name="checkout",
    ),
    path(
        "success/<int:course_id>/",
        views.PaymentSuccessView.as_view(),
        name="success",
    ),
    path(
        "cancel/<int:course_id>/",
        views.PaymentCancelView.as_view(),
        name="cancel",
    ),
    path(
        "status/<int:course_id>/",
        views.PaymentStatusView.as_view(),
        name="status",
    ),
]