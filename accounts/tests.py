from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

PASSWORD = "StrongPass!123"


class EmailOtpRegistrationTests(TestCase):
    """Covers the email-OTP registration flow (requirements, section 14)."""

    def _register(self, username="student1", email="student1@example.com"):
        return self.client.post(
            reverse("register"),
            {
                "username": username,
                "email": email,
                "first_name": "",
                "last_name": "",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

    def _login(self, username="student1"):
        return self.client.post(
            reverse("login"),
            {"username": username, "password": PASSWORD},
        )

    # Case 1 — successful registration: OTP received, correct OTP, activation,
    # login succeeds.
    def test_case_1_successful_registration_activates_and_allows_login(self):
        response = self._register()
        self.assertRedirects(response, reverse("verify_email"))

        user = User.objects.get(username="student1")
        self.assertFalse(user.is_active)

        # An OTP was generated, stored and "emailed" (locmem test backend).
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Verify Your E-Learning Account")
        verification = user.email_verification
        self.assertRegex(verification.otp, r"^\d{6}$")
        self.assertIs(verification.is_verified, False)

        # Enter the correct OTP.
        response = self.client.post(
            reverse("verify_email"), {"otp": verification.otp}
        )
        user.refresh_from_db()
        user.email_verification.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verification.is_verified)
        self.assertEqual(user.email_verification.otp, "")  # code was burned

        # Verified users can log in.
        response = self._login()
        self.assertRedirects(response, reverse("dashboard"))

    # Case 2 — wrong OTP is rejected, the user stays unverified/inactive.
    def test_case_2_wrong_otp_is_rejected(self):
        self._register()
        user = User.objects.get(username="student1")
        correct = user.email_verification.otp
        wrong = "999999" if correct != "999999" else "000000"

        response = self.client.post(
            reverse("verify_email"), {"otp": wrong}, follow=True
        )
        user.refresh_from_db()
        self.assertContains(response, "Invalid OTP.")
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verification.is_verified)
# Case 3 — an expired OTP cannot be used.
    def test_case_3_expired_otp_is_rejected(self):
        self._register()
        user = User.objects.get(username="student1")
        verification = user.email_verification
        verification.expires_at = timezone.now() - timedelta(minutes=1)
        verification.save(update_fields=["expires_at"])

        response = self.client.post(
            reverse("verify_email"), {"otp": verification.otp}, follow=True
        )
        user.refresh_from_db()
        self.assertContains(response, "OTP has expired")
        self.assertFalse(user.is_active)

    # Case 4 — resend invalidates OTP 1; only OTP 2 works.
    def test_case_4_resend_invalidates_previous_otp(self):
        self._register()
        user = User.objects.get(username="student1")
        old = user.email_verification.otp

        # Move the last email far enough back so the 60s cooldown doesn't block.
        user.email_verification.created_at = timezone.now() - timedelta(seconds=120)
        user.email_verification.save(update_fields=["created_at"])

        self.client.post(reverse("resend_otp"))
        fresh = User.objects.get(username="student1")
        new = fresh.email_verification.otp
        self.assertNotEqual(old, new)
        self.assertEqual(len(mail.outbox), 2)  # registration + resend

        # The old code no longer verifies...
        response = self.client.post(
            reverse("verify_email"), {"otp": old}, follow=True
        )
        self.assertContains(response, "Invalid OTP.")
        self.assertFalse(User.objects.get(username="student1").is_active)

        # ...but the new one does.
        self.client.post(reverse("verify_email"), {"otp": new})
        self.assertTrue(User.objects.get(username="student1").is_active)

    # Resend cooldown: repeated requests within 60s are blocked.
    def test_resend_cooldown_blocks_repeated_requests(self):
        self._register()
        self.assertEqual(len(mail.outbox), 1)
        response = self.client.post(reverse("resend_otp"), follow=True)
        self.assertContains(response, "seconds before requesting a new OTP")
        self.assertEqual(len(mail.outbox), 1)  # no extra email was sent

    # If the OTP email cannot be sent (e.g. SMTP misconfigured), the
    # half-registered account is removed and the user is told what happened —
    # never a silent failure.
    @mock.patch(
        "accounts.views.send_mail",
        side_effect=OSError("SMTP connection refused"),
    )
    def test_failed_otp_email_rolls_back_registration(self, mock_send):
        response = self.client.post(
            reverse("register"),
            {
                "username": "student1",
                "email": "student1@example.com",
                "first_name": "",
                "last_name": "",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
            follow=True,
        )
        self.assertContains(response, "could not send the verification email")
        self.assertFalse(User.objects.filter(username="student1").exists())

    # Case 5 — an unverified account cannot log in.
    def test_case_5_unverified_user_cannot_log_in(self):
        self._register()
        response = self._login()
        # Correct credentials on an unverified account redirect to OTP page.
        self.assertRedirects(response, reverse("verify_email"))
        user = User.objects.get(username="student1")
        self.assertFalse(user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)

    # Case 7 — duplicate email is rejected.
    def test_case_7_duplicate_email_is_rejected(self):
        self._register()
        response = self._register(username="student2", email="student1@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="student2").exists())
        self.assertContains(response, "already exists")

    # Case 8 — duplicate username is rejected.
    def test_case_8_duplicate_username_is_rejected(self):
        self._register()
        response = self._register(username="student1", email="student2@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="student2@example.com").exists())
        self.assertContains(response, "already exists")


class ExistingActiveUserTests(TestCase):
    """Accounts created before this feature (is_active=True, no OTP row)
    must keep logging in normally — nothing breaks for existing users."""

    def test_existing_active_user_can_log_in_without_verification(self):
        User.objects.create_user(
            username="oldstudent",
            email="old@example.com",
            password=PASSWORD,
        )
        response = self.client.post(
            reverse("login"),
            {"username": "oldstudent", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("dashboard"))
