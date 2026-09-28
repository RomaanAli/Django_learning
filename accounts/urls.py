from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify_email"),
    path("resend-otp/", views.ResendOtpView.as_view(), name="resend_otp"),
    path("google-check/", views.google_check, name="google_check"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.ProfileEditView.as_view(), name="profile_edit"),
]