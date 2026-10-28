from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from courses.models import Course, Enrollment, Lesson
from payments.models import Payment

User = get_user_model()

PASSWORD = "StrongPass!123"


class CourseApiTests(TestCase):
    """API tests for courses."""

    def setUp(self):
        self.anonymous = User.objects.create_user(
            username="anon", email="anon@example.com", password=PASSWORD
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password=PASSWORD,
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.other_instructor = User.objects.create_user(
            username="instructor2",
            email="instructor2@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password=PASSWORD,
            role=User.ROLE_ADMIN,
        )
        self.published = Course.objects.create(
            title="Published Course",
            description="A published course",
            price=0,
            is_published=True,
            instructor=self.instructor,
        )
        self.draft = Course.objects.create(
            title="Draft Course",
            description="A draft course",
            price=0,
            is_published=False,
            instructor=self.instructor,
        )
        self.paid = Course.objects.create(
            title="Paid Course",
            description="A paid course",
            price=9.99,
            is_published=True,
            instructor=self.instructor,
        )

    def _token(self, user):
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": PASSWORD},
        )
        return client, response.data["access"]

    def test_anonymous_list_returns_only_published(self):
        client = APIClient()
        response = client.get(reverse("api_course_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["title"], "Published Course")

    def test_anonymous_post_course_returns_401(self):
        client = APIClient()
        response = client.post(
            reverse("api_course_list"),
            {"title": "New", "description": "D", "price": "0"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_post_course_returns_403(self):
        client, token = self._token(self.student)
        response = client.post(
            reverse("api_course_list"),
            {"title": "New", "description": "D", "price": "0"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_delete_not_available(self):
        client, token = self._token(self.instructor)
        response = client.delete(
            reverse("api_course_detail", args=[self.draft.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_list_search_and_ordering(self):
        client, token = self._token(self.admin)
        response = client.get(
            reverse("api_course_list"),
            {"search": "Published", "ordering": "price"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)
        self.assertTrue(response.data["count"] >= 3)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_draft_anonymous_returns_404(self):
        client = APIClient()
        response = client.get(reverse("api_course_detail", args=[self.draft.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_draft_owner_returns_200(self):
        client, token = self._token(self.instructor)
        response = client.get(
            reverse("api_course_detail", args=[self.draft.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_paid_course_listing_access(self):
        client = APIClient()
        response = client.get(reverse("api_course_list"))
        self.assertEqual(len(response.data["results"]), 3)


class LessonApiTests(TestCase):
    """API tests for lessons."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password=PASSWORD,
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.other_instructor = User.objects.create_user(
            username="instructor2",
            email="instructor2@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password=PASSWORD,
            role=User.ROLE_ADMIN,
        )
        self.published = Course.objects.create(
            title="Published Course",
            description="D",
            price=0,
            is_published=True,
            instructor=self.instructor,
        )
        self.draft = Course.objects.create(
            title="Draft Course",
            description="D",
            price=0,
            is_published=False,
            instructor=self.instructor,
        )
        self.lesson = Lesson.objects.create(
            course=self.published,
            title="First Lesson",
            content="Content",
            order=1,
        )

    def _token(self, user):
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": PASSWORD},
        )
        return client, response.data["access"]

    def test_enrolled_student_lists_lessons(self):
        client, token = self._token(self.student)
        response = client.get(
            reverse("api_lesson_list", args=[self.published.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "First Lesson")

    def test_instructor_creates_lesson_on_own_course(self):
        client, token = self._token(self.instructor)
        response = client.post(
            reverse("api_lesson_list", args=[self.draft.pk]),
            {"title": "New Lesson", "content": "D", "order": 1},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Lesson.objects.filter(title="New Lesson").exists())

    def test_instructor_cant_create_lesson_on_others_course(self):
        client, token = self._token(self.other_instructor)
        response = client.post(
            reverse("api_lesson_list", args=[self.published.pk]),
            {"title": "Sneaky", "content": "D", "order": 1},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Lesson.objects.filter(title="Sneaky").exists())

    def test_lesson_under_wrong_parent_returns_404(self):
        client, token = self._token(self.instructor)
        response = client.get(
            reverse("api_lesson_detail", args=[self.draft.pk, self.lesson.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class EnrollmentApiTests(TestCase):
    """API tests for enrollments."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password=PASSWORD,
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.other_instructor = User.objects.create_user(
            username="instructor2",
            email="instructor2@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password=PASSWORD,
            role=User.ROLE_ADMIN,
        )
        self.published = Course.objects.create(
            title="Published Course",
            description="D",
            price=0,
            is_published=True,
            instructor=self.instructor,
        )
        self.draft = Course.objects.create(
            title="Draft Course",
            description="D",
            price=0,
            is_published=False,
            instructor=self.instructor,
        )
        self.paid = Course.objects.create(
            title="Paid Course",
            description="D",
            price=19.99,
            is_published=True,
            instructor=self.instructor,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, course=self.published
        )

    def _token(self, user):
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": PASSWORD},
        )
        return client, response.data["access"]

    def test_enrollment_free_course(self):
        other_course = Course.objects.create(
            title="Other Free",
            description="D",
            price=0,
            is_published=True,
            instructor=self.other_instructor,
        )
        client, token = self._token(self.student)
        response = client.post(
            reverse("api_enrollment_list"),
            {"course": other_course.pk},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=other_course).exists()
        )

    def test_enrollment_duplicate_returns_400(self):
        client, token = self._token(self.student)
        response = client.post(
            reverse("api_enrollment_list"),
            {"course": self.published.pk},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = client.post(
            reverse("api_enrollment_list"),
            {"course": self.published.pk},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_enrollment_paid_course_returns_400(self):
        client, token = self._token(self.student)
        response = client.post(
            reverse("api_enrollment_list"),
            {"course": self.paid.pk},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("paid", response.data[0].lower())

    def test_enrollment_another_users_detail_returns_404(self):
        client, token = self._token(self.student)
        response = client.get(
            reverse("api_enrollment_detail", args=[self.enrollment.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        other_student = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password=PASSWORD,
        )
        other_enrollment = Enrollment.objects.create(
            student=other_student, course=self.published
        )
        client2, token2 = self._token(other_student)
        response2 = client2.get(
            reverse("api_enrollment_detail", args=[self.enrollment.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token2}",
        )
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

class MeApiTests(TestCase):
    """API tests for the /api/me/ endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=PASSWORD,
            role=User.ROLE_STUDENT,
        )

    def _token(self, user):
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": PASSWORD},
        )
        return client, response.data["access"]

    def test_me_returns_exact_keys(self):
        client, token = self._token(self.user)
        response = client.get(reverse("api_me"), HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), {"id", "username", "email", "email_verified"})
        self.assertEqual(response.data["id"], self.user.pk)
        self.assertEqual(response.data["username"], "testuser")
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertFalse(response.data["email_verified"])

    def test_me_with_verified_email(self):
        from django.utils import timezone
        from datetime import timedelta
        from accounts.models import EmailVerification

        EmailVerification.objects.create(
            user=self.user,
            otp="123456",
            expires_at=timezone.now() + timedelta(minutes=5),
            is_verified=True,
        )
        client, token = self._token(self.user)
        response = client.get(reverse("api_me"), HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertTrue(response.data["email_verified"])


class PaymentsApiTests(TestCase):
    """API tests for payments."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password=PASSWORD,
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.other_user = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password=PASSWORD,
        )
        self.published = Course.objects.create(
            title="Published Course",
            description="D",
            price=0,
            is_published=True,
            instructor=self.instructor,
        )
        self.payment = Payment.objects.create(
            user=self.user,
            course=self.published,
            stripe_session_id="cs_test_1",
            stripe_payment_intent="pi_test_1",
            amount="19.99",
            currency="usd",
            status=Payment.Status.PAID,
        )

    def _token(self, user):
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": PASSWORD},
        )
        return client, response.data["access"]

    def test_payment_list_shows_only_own(self):
        client, token = self._token(self.user)
        response = client.get(reverse("api_payment_list"), HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_payment_detail_another_users_returns_404(self):
        client, token = self._token(self.user)
        response = client.get(
            reverse("api_payment_detail", args=[self.payment.pk]),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
