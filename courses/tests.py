from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Course, Enrollment, Lesson

User = get_user_model()

PASSWORD = "StrongPass!123"


class InstructorCourseOwnershipTests(TestCase):
    """An instructor may only manage the courses they own."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.other = User.objects.create_user(
            username="instructor2",
            email="instructor2@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.student = User.objects.create_user(
            username="student1", email="student1@example.com", password=PASSWORD
        )
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password=PASSWORD,
            role=User.ROLE_ADMIN,
        )
        self.course = Course.objects.create(
            title="Django Basics",
            description="Learn Django.",
            price=49.99,
            instructor=self.instructor,
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title="Models", content="About models.", order=1
        )

    def test_is_managed_by_is_true_for_the_owner(self):
        self.assertTrue(self.course.is_managed_by(self.instructor))

    def test_is_managed_by_is_false_for_another_instructor(self):
        self.assertFalse(self.course.is_managed_by(self.other))

    def test_is_managed_by_is_false_for_a_student(self):
        self.assertFalse(self.course.is_managed_by(self.student))

    def test_is_managed_by_is_true_for_an_admin(self):
        self.assertTrue(self.course.is_managed_by(self.admin))

    def test_is_managed_by_is_false_for_an_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(self.course.is_managed_by(AnonymousUser()))

    def test_course_list_only_shows_own_courses(self):
        other_course = Course.objects.create(
            title="Other",
            description="Not mine.",
            price=0,
            instructor=self.other,
        )
        self.client.force_login(self.instructor)
        response = self.client.get(reverse("instructor_course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertNotContains(response, other_course.title)

    def test_students_cannot_reach_the_course_management_pages(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("instructor_course_list"))
        self.assertEqual(response.status_code, 403)

    def test_owner_can_open_the_edit_page(self):
        self.client.force_login(self.instructor)
        response = self.client.get(
            reverse("instructor_course_edit", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_a_different_instructor_cannot_open_the_edit_page(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("instructor_course_edit", args=[self.course.pk]), follow=True
        )
        self.assertRedirects(response, reverse("instructor_course_list"))
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Django Basics")

    def test_a_different_instructor_cannot_post_an_edit(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("instructor_course_edit", args=[self.course.pk]),
            {"title": "Hijacked", "description": "Nope.", "price": "0"},
        )
        self.assertRedirects(response, reverse("instructor_course_list"))
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Django Basics")



class InstructorCourseManagementTests(TestCase):
    """Creating, editing, publishing courses and adding lessons."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor1",
            email="instructor1@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        self.client.force_login(self.instructor)

    def test_create_course_assigns_the_instructor_and_starts_as_draft(self):
        response = self.client.post(
            reverse("instructor_course_create"),
            {"title": "New course", "description": "Fresh content.", "price": "19.99"},
        )
        self.assertEqual(response.status_code, 302)

        course = Course.objects.get(title="New course")
        self.assertEqual(course.instructor, self.instructor)
        self.assertFalse(course.is_published)
        self.assertRedirects(
            response, reverse("instructor_course_edit", args=[course.pk])
        )

    def test_edit_course_saves_the_changes(self):
        course = Course.objects.create(
            title="Old title",
            description="Old description.",
            price=10,
            instructor=self.instructor,
        )
        response = self.client.post(
            reverse("instructor_course_edit", args=[course.pk]),
            {"title": "New title", "description": "New description.", "price": "25"},
        )
        self.assertRedirects(
            response, reverse("instructor_course_edit", args=[course.pk])
        )
        course.refresh_from_db()
        self.assertEqual(course.title, "New title")
        self.assertEqual(str(course.price), "25.00")

    def test_publish_toggles_the_published_flag(self):
        course = Course.objects.create(
            title="Draft",
            description="...",
            price=0,
            instructor=self.instructor,
        )
        response = self.client.post(
            reverse("instructor_course_publish", args=[course.pk])
        )
        self.assertRedirects(
            response, reverse("instructor_course_edit", args=[course.pk])
        )
        course.refresh_from_db()
        self.assertTrue(course.is_published)


    def test_add_lesson_attaches_it_to_the_course(self):
        course = Course.objects.create(
            title="With lessons",
            description="...",
            price=0,
            instructor=self.instructor,
        )
        response = self.client.post(
            reverse("instructor_lesson_create", args=[course.pk]),
            {"title": "Lesson one", "content": "Body", "order": 1},
        )
        self.assertRedirects(
            response, reverse("instructor_course_edit", args=[course.pk])
        )
        self.assertTrue(course.lessons.filter(title="Lesson one").exists())

    def test_edit_lesson_updates_the_content(self):
        course = Course.objects.create(
            title="With lessons",
            description="...",
            price=0,
            instructor=self.instructor,
        )
        lesson = Lesson.objects.create(
            course=course, title="Lesson one", content="Body", order=1
        )
        response = self.client.post(
            reverse("instructor_lesson_edit", args=[lesson.pk]),
            {"title": "Lesson renamed", "content": "New body", "order": 2},
        )
        self.assertRedirects(
            response, reverse("instructor_course_edit", args=[course.pk])
        )
        lesson.refresh_from_db()
        self.assertEqual(lesson.title, "Lesson renamed")
        self.assertEqual(lesson.order, 2)

    def test_delete_lesson_removes_it(self):
        course = Course.objects.create(
            title="With lessons",
            description="...",
            price=0,
            instructor=self.instructor,
        )
        lesson = Lesson.objects.create(
            course=course, title="Lesson one", content="Body", order=1
        )
        response = self.client.post(
            reverse("instructor_lesson_edit", args=[lesson.pk]),
            {"action": "delete"},
        )
        self.assertRedirects(
            response, reverse("instructor_course_edit", args=[course.pk])
        )
        self.assertFalse(Lesson.objects.filter(pk=lesson.pk).exists())

    def test_another_instructor_cannot_add_a_lesson(self):
        other = User.objects.create_user(
            username="instructor2",
            email="instructor2@example.com",
            password=PASSWORD,
            role=User.ROLE_INSTRUCTOR,
        )
        course = Course.objects.create(
            title="Not yours",
            description="...",
            price=0,
            instructor=self.instructor,
        )
        self.client.force_login(other)
        response = self.client.post(
            reverse("instructor_lesson_create", args=[course.pk]),
            {"title": "Sneaky lesson", "content": "Body", "order": 1},
        )
        self.assertRedirects(response, reverse("instructor_course_list"))
        self.assertFalse(course.lessons.filter(title="Sneaky lesson").exists())


class EnrollmentTests(TestCase):
    """Students can enrol in published courses."""

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
        self.course = Course.objects.create(
            title="Free course",
            description="...",
            price=0,
            is_published=True,
            instructor=self.instructor,
        )

    def test_student_can_enrol_in_a_free_course(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("enroll_course", args=[self.course.pk]))
        self.assertRedirects(response, reverse("course_detail", args=[self.course.pk]))
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, course=self.course
            ).exists()
        )
