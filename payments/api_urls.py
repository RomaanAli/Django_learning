from django.urls import path

from . import api_views

urlpatterns = [
    path("", api_views.PaymentListCreateView.as_view(), name="api_payment_list"),
    path(
        "<int:pk>/",
        api_views.PaymentDetailView.as_view(),
        name="api_payment_detail",
    ),
]
