from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from rest_framework.test import APIClient
from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialApp
from accounts.models import InstructorDocument, EmailVerification
from accounts.adapters import SocialAccountAdapter
from courses.models import Course, Lesson
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

User = get_user_model()


def _attach_messages_and_session(req):
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session.save()
    messages = FallbackStorage(req)
    setattr(req, '_messages', messages)


class ApprovalGateModelTests(TestCase):

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            password="Password123!",
            role=User.ROLE_ADMIN,
        )
        self.student = User.objects.create_user(
            username="studentuser",
            email="student@example.com",
            password="Password123!",
            role=User.ROLE_STUDENT,
        )
        self.instructor = User.objects.create_user(
            username="pendinginst",
            email="inst@example.com",
            password="Password123!",
            role=User.ROLE_INSTRUCTOR,
            is_approved_instructor=False,
        )

    def test_can_teach_property(self):
        self.assertTrue(self.admin_user.can_teach)
        self.assertFalse(self.student.can_teach)

        self.student.is_approved_instructor = True
        self.student.save()
        self.assertFalse(self.student.can_teach)

        self.assertFalse(self.instructor.can_teach)

        self.instructor.is_approved_instructor = True
        self.instructor.save()
        self.assertTrue(self.instructor.can_teach)

    def test_approve_promotes_student_and_sets_flag(self):
        doc = InstructorDocument.objects.create(
            user=self.student,
            file=SimpleUploadedFile("cert.pdf", b"%PDF-1.4 test content", content_type="application/pdf"),
            status=InstructorDocument.STATUS_PENDING,
        )

        doc.approve(reviewer=self.admin_user)

        doc.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(doc.status, InstructorDocument.STATUS_APPROVED)
        self.assertEqual(self.student.role, User.ROLE_INSTRUCTOR)
        self.assertTrue(self.student.is_approved_instructor)
        self.assertTrue(self.student.can_teach)

    def test_deny_application_sets_status_and_flag(self):
        doc = InstructorDocument.objects.create(
            user=self.instructor,
            file=SimpleUploadedFile("cert.pdf", b"%PDF-1.4 test content", content_type="application/pdf"),
            status=InstructorDocument.STATUS_PENDING,
        )

        doc.deny(reviewer=self.admin_user, reason="Document invalid")

        doc.refresh_from_db()
        self.instructor.refresh_from_db()
        self.assertEqual(doc.status, InstructorDocument.STATUS_DENIED)
        self.assertFalse(self.instructor.is_approved_instructor)
        self.assertFalse(self.instructor.can_teach)


class RegistrationApprovalGateTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_register_student_no_document_required(self):
        data = {
            "role": "student",
            "username": "newstudent",
            "email": "newstudent@example.com",
            "first_name": "New",
            "last_name": "Student",
            "password1": "Password123!",
            "password2": "Password123!",
        }
        resp = self.client.post(reverse("register"), data)
        self.assertRedirects(resp, reverse("verify_email"))
        user = User.objects.get(username="newstudent")
        self.assertFalse(user.is_active)  # Pending OTP
        self.assertEqual(user.role, User.ROLE_STUDENT)
        self.assertFalse(user.is_approved_instructor)

        # No document created
        self.assertFalse(InstructorDocument.objects.filter(user=user).exists())

    def test_register_instructor_without_document_fails(self):
        data = {
            "role": "instructor",
            "username": "newinst_fail",
            "email": "newinst_fail@example.com",
            "first_name": "New",
            "last_name": "Instructor",
            "password1": "Password123!",
            "password2": "Password123!",
        }
        resp = self.client.post(reverse("register"), data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Document is required for instructor registration.")
        self.assertFalse(User.objects.filter(username="newinst_fail").exists())

    def test_register_instructor_invalid_file_extension(self):
        bad_file = SimpleUploadedFile("script.sh", b"#!/bin/bash echo hacked", content_type="text/plain")
        data = {
            "role": "instructor",
            "username": "newinst_badext",
            "email": "badext@example.com",
            "first_name": "New",
            "last_name": "Instructor",
            "password1": "Password123!",
            "password2": "Password123!",
            "document": bad_file,
        }
        resp = self.client.post(reverse("register"), data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Only PDF, PNG or JPG documents are accepted")

    def test_register_instructor_valid_document_success(self):
        valid_pdf = SimpleUploadedFile("degree.pdf", b"%PDF-1.4 valid test file", content_type="application/pdf")
        data = {
            "role": "instructor",
            "username": "newinst_ok",
            "email": "newinst_ok@example.com",
            "first_name": "New",
            "last_name": "Instructor",
            "password1": "Password123!",
            "password2": "Password123!",
            "document": valid_pdf,
        }
        resp = self.client.post(reverse("register"), data)
        self.assertRedirects(resp, reverse("verify_email"))

        user = User.objects.get(username="newinst_ok")
        self.assertFalse(user.is_active)  # Pending OTP
        self.assertFalse(user.is_approved_instructor)

        # Verify document was created
        doc = InstructorDocument.objects.filter(user=user).first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.status, InstructorDocument.STATUS_PENDING)

        # After verifying OTP, user has role instructor and is_approved_instructor=False
        otp = EmailVerification.objects.get(user=user).otp
        self.client.post(reverse("verify_email"), {"otp": otp})
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.ROLE_INSTRUCTOR)
        self.assertFalse(user.is_approved_instructor)
        self.assertFalse(user.can_teach)


class WebPermissionGateTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="superboss", email="boss@example.com", password="Password123!", role=User.ROLE_ADMIN
        )
        self.approved_inst1 = User.objects.create_user(
            username="appinst1", email="app1@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=True
        )
        self.approved_inst2 = User.objects.create_user(
            username="appinst2", email="app2@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=True
        )
        self.pending_inst = User.objects.create_user(
            username="pendinst", email="pend@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=False
        )
        InstructorDocument.objects.create(
            user=self.pending_inst,
            file=SimpleUploadedFile("cert_pending.pdf", b"%PDF-1.4 pending test", content_type="application/pdf"),
            status=InstructorDocument.STATUS_PENDING,
        )
        self.denied_inst = User.objects.create_user(
            username="deninst", email="den@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=False
        )
        InstructorDocument.objects.create(
            user=self.denied_inst,
            file=SimpleUploadedFile("cert.pdf", b"%PDF-1.4 test", content_type="application/pdf"),
            status=InstructorDocument.STATUS_DENIED,
            review_note="Incomplete degree transcript",
        )
        self.student = User.objects.create_user(
            username="normstudent", email="student@example.com", password="Password123!",
            role=User.ROLE_STUDENT, is_approved_instructor=False
        )
        self.course1 = Course.objects.create(
            title="Course 1", description="Description 1", price=10.0, instructor=self.approved_inst1, is_published=True
        )
        self.lesson1 = Lesson.objects.create(
            course=self.course1, title="Lesson 1", content="Content 1", order=1
        )

    def test_anonymous_access_redirects_to_login(self):
        resp = self.client.get(reverse("instructor_course_create"))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('instructor_course_create')}")

    def test_student_access_denied(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse("instructor_course_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("instructor_course_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("instructor_course_edit", args=[self.course1.pk])).status_code, 403)

    def test_pending_instructor_cannot_create_course(self):
        self.client.force_login(self.pending_inst)
        resp_get = self.client.get(reverse("instructor_course_create"))
        self.assertRedirects(resp_get, reverse("instructor_dashboard"))

        resp_post = self.client.post(reverse("instructor_course_create"), {"title": "Test", "description": "Desc"})
        self.assertRedirects(resp_post, reverse("instructor_dashboard"))

    def test_pending_instructor_cannot_edit_course(self):
        self.client.force_login(self.pending_inst)
        resp = self.client.get(reverse("instructor_course_edit", args=[self.course1.pk]))
        self.assertRedirects(resp, reverse("instructor_dashboard"))

    def test_pending_instructor_dashboard_shows_status_card(self):
        self.client.force_login(self.pending_inst)
        resp = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Instructor application under review")
        self.assertNotContains(resp, "New course")

    def test_denied_instructor_dashboard_shows_reason(self):
        self.client.force_login(self.denied_inst)
        resp = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Application Denied")
        self.assertContains(resp, "Incomplete degree transcript")
        self.assertContains(resp, "Upload a new qualification document")

    def test_approved_instructor_can_create_and_edit_own_course(self):
        self.client.force_login(self.approved_inst1)
        resp_dash = self.client.get(reverse("instructor_dashboard"))
        self.assertEqual(resp_dash.status_code, 200)
        self.assertContains(resp_dash, "Instructor Workspace")
        self.assertContains(resp_dash, "New course")

        resp_get = self.client.get(reverse("instructor_course_create"))
        self.assertEqual(resp_get.status_code, 200)

        # Edit own course
        resp_edit = self.client.get(reverse("instructor_course_edit", args=[self.course1.pk]))
        self.assertEqual(resp_edit.status_code, 200)

        # Peer approved instructor cannot edit course1
        self.client.force_login(self.approved_inst2)
        r_peer = self.client.get(reverse("instructor_course_edit", args=[self.course1.pk]))
        self.assertRedirects(r_peer, reverse("instructor_course_list"))

    def test_admin_permissions(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("instructor_course_create")).status_code, 200)
        # Admin can edit any course
        self.assertEqual(self.client.get(reverse("instructor_course_edit", args=[self.course1.pk])).status_code, 200)

    def test_navbar_links_per_role(self):
        # Approved instructor: New Course link present
        self.client.force_login(self.approved_inst1)
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "New Course")
        self.assertContains(resp, "My Courses")

        # Pending instructor: Approval Pending shown, New Course not shown
        self.client.force_login(self.pending_inst)
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "New Course")
        self.assertNotContains(resp, "My Courses")
        self.assertContains(resp, "Approval Pending")

        # Student: no instructor management links
        self.client.force_login(self.student)
        resp = self.client.get(reverse("home"))
        self.assertNotContains(resp, "New Course")
        self.assertNotContains(resp, "Approval Pending")


class GoogleRoleAdapterTests(TestCase):

    def setUp(self):
        self.rf = RequestFactory()
        self.adapter = SocialAccountAdapter()
        self.client = Client()

    def test_set_role_endpoint(self):
        # Test modern set_role endpoint used by register page
        resp_stud = self.client.post(reverse("set_role"), {"role": "student"})
        self.assertEqual(resp_stud.status_code, 200)
        self.assertEqual(self.client.session.get("pending_signup_role"), "student")

        resp_inst = self.client.post(reverse("set_role"), {"role": "instructor"})
        self.assertEqual(resp_inst.status_code, 200)
        self.assertEqual(self.client.session.get("pending_signup_role"), "instructor")

    def test_choose_role_redirects_to_register(self):
        # Legacy choose_role gracefully redirects to register
        resp = self.client.get(reverse("choose_role"))
        self.assertRedirects(resp, reverse("register"))

        resp_role = self.client.get(f"{reverse('choose_role')}?role=instructor")
        self.assertRedirects(resp_role, f"{reverse('register')}?role=instructor")

    def test_pre_social_login_existing_user_unchanged(self):
        user = User.objects.create_user(
            username="existing_guser", email="guser@example.com", role=User.ROLE_STUDENT, is_approved_instructor=False
        )
        account = SocialAccount(user=user, provider="google", uid="12345")
        login = SocialLogin(user=user, account=account)

        req = self.rf.get("/accounts/google/login/")
        req.session = {"pending_signup_role": "instructor"}  # Forged or stale session

        self.adapter.pre_social_login(req, login)

        user.refresh_from_db()
        self.assertEqual(user.role, User.ROLE_STUDENT)
        self.assertFalse(user.is_approved_instructor)

    def test_pre_social_login_new_user_defaults_to_student(self):
        user = User(username="new_guser", email="new_guser@example.com")
        account = SocialAccount(user=user, provider="google", uid="54321")
        login = SocialLogin(user=user, account=account)
        login.state = {}

        req = self.rf.get("/accounts/google/login/")
        _attach_messages_and_session(req)

        self.adapter.pre_social_login(req, login)
        self.assertEqual(req.session.get("_google_new_user_role"), User.ROLE_STUDENT)

        saved = self.adapter.save_user(req, login)
        self.assertEqual(saved.role, User.ROLE_STUDENT)
        self.assertFalse(saved.is_approved_instructor)
        self.assertFalse(saved.can_teach)

    def test_pre_social_login_new_user_with_instructor_role(self):
        user = User(username="new_ginst", email="new_ginst@example.com")
        account = SocialAccount(user=user, provider="google", uid="99999")
        login = SocialLogin(user=user, account=account)
        login.state = {}

        req = self.rf.get("/accounts/google/login/")
        _attach_messages_and_session(req)
        req.session["pending_signup_role"] = "instructor"

        self.adapter.pre_social_login(req, login)

        # Role should be popped from session
        self.assertNotIn("pending_signup_role", req.session)
        self.assertEqual(req.session.get("_google_new_user_role"), "instructor")

        # save_user sets role and is_approved_instructor=False
        saved = self.adapter.save_user(req, login)
        self.assertEqual(saved.role, User.ROLE_INSTRUCTOR)
        self.assertFalse(saved.is_approved_instructor)
        self.assertFalse(saved.can_teach)

    def test_pre_social_login_new_user_with_student_role(self):
        user = User(username="new_gstud", email="new_gstud@example.com")
        account = SocialAccount(user=user, provider="google", uid="88888")
        login = SocialLogin(user=user, account=account)
        login.state = {}

        req = self.rf.get("/accounts/google/login/")
        _attach_messages_and_session(req)
        req.session["pending_signup_role"] = "student"

        self.adapter.pre_social_login(req, login)

        self.assertNotIn("pending_signup_role", req.session)
        self.assertEqual(req.session.get("_google_new_user_role"), "student")

        saved = self.adapter.save_user(req, login)
        self.assertEqual(saved.role, User.ROLE_STUDENT)
        self.assertFalse(saved.is_approved_instructor)
        self.assertFalse(saved.can_teach)

    def test_google_instructor_login_redirect_to_dashboard(self):
        from accounts.adapters import AccountAdapter
        acc_adapter = AccountAdapter()

        ginst = User.objects.create_user(
            username="ginst_noupload", email="noupload@example.com", role=User.ROLE_INSTRUCTOR, is_approved_instructor=False
        )
        req = self.rf.get("/")
        req.user = ginst

        redir = acc_adapter.get_login_redirect_url(req)
        self.assertEqual(redir, reverse("instructor_dashboard"))


class ApiPermissionGateTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.approved_inst = User.objects.create_user(
            username="api_app_inst", email="api_app@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=True
        )
        self.pending_inst = User.objects.create_user(
            username="api_pend_inst", email="api_pend@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=False
        )
        self.denied_inst = User.objects.create_user(
            username="api_den_inst", email="api_den@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=False
        )
        self.student = User.objects.create_user(
            username="api_stud", email="api_stud@example.com", password="Password123!",
            role=User.ROLE_STUDENT, is_approved_instructor=False
        )
        self.course = Course.objects.create(
            title="API Course", description="Desc", price=0, instructor=self.approved_inst, is_published=True
        )

    def test_anonymous_post_course_fails(self):
        resp = self.client.post("/api/courses/", {"title": "New Course", "description": "Desc", "price": 0})
        self.assertIn(resp.status_code, (401, 403))

    def test_student_post_course_fails(self):
        self.client.force_authenticate(user=self.student)
        resp = self.client.post("/api/courses/", {"title": "New Course", "description": "Desc", "price": 0})
        self.assertEqual(resp.status_code, 403)

    def test_pending_instructor_post_course_fails(self):
        self.client.force_authenticate(user=self.pending_inst)
        resp = self.client.post("/api/courses/", {"title": "New Course", "description": "Desc", "price": 0})
        self.assertEqual(resp.status_code, 403)

    def test_denied_instructor_post_course_fails(self):
        self.client.force_authenticate(user=self.denied_inst)
        resp = self.client.post("/api/courses/", {"title": "New Course", "description": "Desc", "price": 0})
        self.assertEqual(resp.status_code, 403)

    def test_approved_instructor_post_course_success(self):
        self.client.force_authenticate(user=self.approved_inst)
        resp = self.client.post("/api/courses/", {"title": "Approved Course", "description": "Desc", "price": 0})
        self.assertEqual(resp.status_code, 201)

    def test_approved_instructor_patch_peer_course_fails(self):
        peer = User.objects.create_user(
            username="api_peer_inst", email="peer@example.com", password="Password123!",
            role=User.ROLE_INSTRUCTOR, is_approved_instructor=True
        )
        self.client.force_authenticate(user=peer)
        resp = self.client.patch(f"/api/courses/{self.course.pk}/", {"title": "Hacked Title"})
        self.assertEqual(resp.status_code, 403)

    def test_pending_instructor_post_lesson_fails(self):
        self.client.force_authenticate(user=self.pending_inst)
        resp = self.client.post(f"/api/courses/{self.course.pk}/lessons/", {
            "title": "New Lesson", "content": "Content", "order": 1
        })
        self.assertEqual(resp.status_code, 403)
