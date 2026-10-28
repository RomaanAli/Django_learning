from datetime import timedelta
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone

from .admin import InstructorDocumentAdmin
from .models import InstructorDocument

from allauth.account.models import EmailAddress

User = get_user_model()

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

    def test_case_1_successful_registration_activates_and_allows_login(self):
        response = self._register()
        self.assertRedirects(response, reverse("verify_email"))

        user = User.objects.get(username="student1")
        self.assertFalse(user.is_active)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Verify Your E-Learning Account")
        verification = user.email_verification
        self.assertRegex(verification.otp, r"^\d{6}$")
        self.assertIs(verification.is_verified, False)

        response = self.client.post(
            reverse("verify_email"), {"otp": verification.otp}
        )
        user.refresh_from_db()
        user.email_verification.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verification.is_verified)
        self.assertEqual(user.email_verification.otp, "")

        response = self._login()
        self.assertRedirects(response, reverse("dashboard"))

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

    def test_case_4_resend_invalidates_previous_otp(self):
        self._register()
        user = User.objects.get(username="student1")
        old = user.email_verification.otp

        user.email_verification.created_at = timezone.now() - timedelta(seconds=120)
        user.email_verification.save(update_fields=["created_at"])

        self.client.post(reverse("resend_otp"))
        fresh = User.objects.get(username="student1")
        new = fresh.email_verification.otp
        self.assertNotEqual(old, new)
        self.assertEqual(len(mail.outbox), 2)

        response = self.client.post(
            reverse("verify_email"), {"otp": old}, follow=True
        )
        self.assertContains(response, "Invalid OTP.")
        self.assertFalse(User.objects.get(username="student1").is_active)

        self.client.post(reverse("verify_email"), {"otp": new})
        self.assertTrue(User.objects.get(username="student1").is_active)

    def test_resend_cooldown_blocks_repeated_requests(self):
        self._register()
        self.assertEqual(len(mail.outbox), 1)
        response = self.client.post(reverse("resend_otp"), follow=True)
        self.assertContains(response, "seconds before requesting a new OTP")
        self.assertEqual(len(mail.outbox), 1)

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

    def test_case_5_unverified_user_cannot_log_in(self):
        self._register()
        response = self._login()
        self.assertRedirects(response, reverse("verify_email"))
        user = User.objects.get(username="student1")
        self.assertFalse(user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_case_7_duplicate_email_is_rejected(self):
        self._register()
        user = User.objects.get(username="student1")
        user.is_active = True
        user.save(update_fields=["is_active"])

        response = self._register(username="student2", email="student1@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="student2").exists())
        self.assertContains(response, "already exists")

    def test_case_7b_retry_with_same_email_after_lost_otp_registers_fresh(self):
        self._register()
        stale_id = User.objects.get(username="student1").pk

        response = self._register()

        self.assertRedirects(response, reverse("verify_email"))
        self.assertFalse(User.objects.filter(pk=stale_id).exists())
        self.assertEqual(User.objects.filter(email="student1@example.com").count(), 1)
        user = User.objects.get(email="student1@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 2)
        self.assertRegex(user.email_verification.otp, r"^\d{6}$")

    @mock.patch(
        "accounts.views._create_or_refresh_otp", side_effect=RuntimeError("boom")
    )
    def test_case_7c_otp_failure_leaves_no_phantom_user(self, _mock):
        response = self._register()
        self.assertRedirects(response, reverse("register"))
        self.assertFalse(User.objects.filter(username="student1").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_case_8_duplicate_username_is_rejected(self):
        self._register()
        response = self._register(username="student1", email="student2@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="student2@example.com").exists())
        self.assertContains(response, "already exists")


class DualLoginAndPasswordResetTests(TestCase):
    """Regression tests for username/email dual login and allauth EmailAddress."""

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

    def test_registration_creates_allauth_email_address(self):
        """Registration must populate allauth's EmailAddress table."""
        self._register()
        user = User.objects.get(username="student1")
        self.assertTrue(
            EmailAddress.objects.filter(user=user, email="student1@example.com").exists(),
            "Expected an EmailAddress row for the newly registered user.",
        )
        ea = EmailAddress.objects.get(user=user, email="student1@example.com")
        self.assertTrue(ea.primary)
        self.assertFalse(ea.verified)

    def test_login_by_email(self):
        """Logging in with the email address (instead of username) works."""
        self._register()
        user = User.objects.get(username="student1")
        user.is_active = True
        user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("login"),
            {"username": "student1@example.com", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_unverified_email_login_redirects_to_verify_email(self):
        """An unverified user logging in by email is sent to OTP verification."""
        self._register()

        response = self.client.post(
            reverse("login"),
            {"username": "student1@example.com", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("verify_email"))
        user = User.objects.get(username="student1")
        self.assertFalse(user.is_active)

    def test_password_reset_known_email_finds_user(self):
        """Password reset for a known, registered email must not say 'Unknown Account'."""
        self._register()
        user = User.objects.get(username="student1")
        user.is_active = True
        user.save(update_fields=["is_active"])

        from django.test import Client
        from django.core import mail as django_mail

        django_mail.outbox.clear()

        c = Client()
        r = c.post("/accounts/password/reset/", {"email": "student1@example.com"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(django_mail.outbox), 1)
        self.assertNotIn("Unknown Account", django_mail.outbox[0].subject)
        self.assertIn("student1@example.com", django_mail.outbox[0].to)


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


class GoogleLoginDiagnosticsTests(TestCase):
    """/accounts/google-check/ must show the exact redirect_uri(s) that have
    to be registered in the Google Cloud Console plus the fix checklist for
    Google's "Access blocked" error page."""

    def _get(self, host="localhost:8000"):
        return self.client.get(reverse("google_check"), SERVER_NAME=host)

    def test_page_lists_both_loopback_redirect_uris(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(
            "http://localhost:8000/accounts/google/login/callback/", content
        )
        self.assertIn(
            "http://127.0.0.1:8000/accounts/google/login/callback/", content
        )

    def test_redirect_uri_follows_the_host_the_visitor_uses(self):
        content = self._get(host="127.0.0.1:8000").content.decode()
        self.assertIn("redirect_uri allauth sends to Google", content)
        self.assertIn(
            "http://127.0.0.1:8000/accounts/google/login/callback/", content
        )

    def test_page_explains_how_to_fix_access_blocked(self):
        content = self._get().content.decode()
        self.assertIn("Access blocked", content)
        self.assertIn("OAuth consent screen", content)
        self.assertIn("Test users", content)
        self.assertIn("Authorized redirect URIs", content)

    def test_client_id_is_masked_not_leaked(self):
        content = self._get().content.decode()
        import os

        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or ""
        if client_id:
            self.assertNotIn(client_id, content)


class RolePermissionTests(TestCase):
    """Role helpers and the role mixins guard the right pages."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student1@example.com", password=PASSWORD
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password=PASSWORD,
            role=User.ROLE_ADMIN,
        )
        self.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password=PASSWORD
        )

    def test_new_users_default_to_the_student_role(self):
        self.assertEqual(self.student.role, User.ROLE_STUDENT)
        self.assertTrue(self.student.is_student)
        self.assertFalse(self.student.is_instructor)
        self.assertFalse(self.student.is_admin)

    def test_role_helpers_follow_the_role_field(self):
        self.assertTrue(self.instructor.is_instructor)
        self.assertFalse(self.instructor.is_student)
        self.assertTrue(self.admin.is_admin)
        self.assertFalse(self.admin.is_instructor)

    def test_instructor_dashboard_is_closed_to_students(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_instructor_dashboard_is_open_to_instructors(self):
        self.client.force_login(self.instructor)
        response = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_instructor_dashboard_is_open_to_admins(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_superusers_pass_the_role_check(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_visitors_are_redirected_to_login(self):
        response = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])


class InstructorApplicationTests(TestCase):
    """Applying to teach uploads one document that stays pending until approved."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student1@example.com", password=PASSWORD
        )
        self.client.force_login(self.student)

    def _upload(self, name="cv.pdf", content_type="application/pdf", content=b"%PDF-1.4"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile(name, content, content_type=content_type)
        return self.client.post(reverse("instructor_apply"), {"file": upload})

    def test_apply_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("instructor_apply"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_apply_page_renders_for_a_student(self):
        response = self.client.get(reverse("instructor_apply"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "instructor")

    def test_upload_creates_a_pending_document(self):
        response = self._upload()
        self.assertRedirects(response, reverse("instructor_apply"))

        document = InstructorDocument.objects.get(user=self.student)
        self.assertEqual(document.status, InstructorDocument.STATUS_PENDING)
        self.assertTrue(document.is_pending)
        self.assertFalse(document.is_approved)
        self.assertIsNone(document.approved_at)
        self.assertIsNone(document.approved_by)

    def test_upload_does_not_promote_the_user_to_instructor(self):
        self._upload()
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_STUDENT)
        self.assertFalse(self.student.is_instructor)

    def test_rejected_file_type_is_not_accepted(self):
        response = self._upload(
            name="malware.exe", content_type="application/octet-stream", content=b"MZ"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InstructorDocument.objects.filter(user=self.student).exists())
        self.assertFormError(
            response.context["form"],
            "file",
            "Only PDF, PNG or JPG documents are accepted "
            "(.pdf, .png, .jpg, .jpeg).",
        )

    def test_file_larger_than_five_megabytes_is_rejected(self):
        response = self._upload(content=b"0" * (5 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InstructorDocument.objects.filter(user=self.student).exists())
        self.assertFormError(
            response.context["form"],
            "file",
            "The file is too large (max 5 MB).",
        )

    def test_instructors_are_redirected_away_from_the_apply_page(self):
        self.student.role = User.ROLE_INSTRUCTOR
        self.student.save(update_fields=["role"])
        response = self.client.get(reverse("instructor_apply"))
        self.assertRedirects(response, reverse("instructor_dashboard"))



class InstructorApprovalTests(TestCase):
    """Approving a document in the admin promotes the applicant."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student1@example.com", password=PASSWORD
        )
        self.document = InstructorDocument.objects.create(
            user=self.student,
            file="instructor_documents/cv.pdf",
            status=InstructorDocument.STATUS_PENDING,
        )
        self.admin = User.objects.create_superuser(
            username="root", email="root@example.com", password=PASSWORD
        )
        self.model_admin = InstructorDocumentAdmin(InstructorDocument, AdminSite())

    def _save(self, status):
        request = RequestFactory().post("/admin/accounts/instructordocument/")
        request.user = self.admin
        self.document.status = status
        self.model_admin.save_model(request, self.document, None, change=True)

    def test_approval_stamps_the_reviewer_and_timestamp(self):
        self._save(InstructorDocument.STATUS_APPROVED)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, InstructorDocument.STATUS_APPROVED)
        self.assertTrue(self.document.is_approved)
        self.assertIsNotNone(self.document.approved_at)
        self.assertEqual(self.document.approved_by, self.admin)

    def test_approval_promotes_the_user_to_instructor(self):
        self._save(InstructorDocument.STATUS_APPROVED)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_INSTRUCTOR)
        self.assertTrue(self.student.is_instructor)

    def test_approval_does_not_downgrade_an_admin(self):
        self.student.role = User.ROLE_ADMIN
        self.student.save(update_fields=["role"])
        self._save(InstructorDocument.STATUS_APPROVED)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_ADMIN)

    def test_pending_document_does_not_promote_the_user(self):
        self._save(InstructorDocument.STATUS_PENDING)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_STUDENT)
        self.assertIsNone(self.document.approved_at)

    def test_denial_keeps_the_user_a_student(self):
        self._save(InstructorDocument.STATUS_DENIED)
        self.student.refresh_from_db()
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, InstructorDocument.STATUS_DENIED)
        self.assertEqual(self.student.role, User.ROLE_STUDENT)


class InstructorDocumentModelTests(TestCase):
    """``InstructorDocument.approve``/``deny`` work outside the admin too."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student1@example.com", password=PASSWORD
        )
        self.document = InstructorDocument.objects.create(
            user=self.student,
            file="instructor_documents/cv.pdf",
            status=InstructorDocument.STATUS_PENDING,
        )
        self.reviewer = User.objects.create_superuser(
            username="root", email="root@example.com", password=PASSWORD
        )

    def test_approve_promotes_the_student(self):
        self.assertTrue(self.document.approve(reviewer=self.reviewer))
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_INSTRUCTOR)
        self.assertTrue(self.document.is_approved)
        self.assertEqual(self.document.approved_by, self.reviewer)
        self.assertIsNotNone(self.document.approved_at)

    def test_approve_is_idempotent(self):
        self.document.approve(reviewer=self.reviewer)
        first_approved_at = self.document.approved_at
        self.assertFalse(self.document.approve(reviewer=self.reviewer))
        self.assertEqual(self.document.approved_at, first_approved_at)

    def test_approve_does_not_downgrade_an_admin(self):
        self.student.role = User.ROLE_ADMIN
        self.student.save(update_fields=["role"])
        self.document.approve(reviewer=self.reviewer)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_ADMIN)

    def test_deny_leaves_the_role_untouched(self):
        self.assertTrue(self.document.deny(reviewer=self.reviewer))
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.ROLE_STUDENT)
        self.assertEqual(self.document.status, InstructorDocument.STATUS_DENIED)

    def test_deny_is_idempotent(self):
        self.document.deny(reviewer=self.reviewer)
        self.assertFalse(self.document.deny(reviewer=self.reviewer))
