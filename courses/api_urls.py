from django.urls import path

from . import api_views

urlpatterns = [
    # Course list/create
    path("", api_views.CourseListCreateView.as_view(), name="api_course_list"),
    # Course detail (public read + owner write)
    path("<int:pk>/", api_views.CourseDetailView.as_view(), name="api_course_detail"),
    # Instructor's courses (admins/superusers see all, instructors see own)
    path(
        "instructor/",
        api_views.InstructorCourseListView.as_view(),
        name="api_instructor_course_list",
    ),
    # Lessons
    path(
        "<int:course_pk>/lessons/",
        api_views.LessonListCreateView.as_view(),
        name="api_lesson_list",
    ),
    path(
        "<int:course_pk>/lessons/<int:pk>/",
        api_views.LessonDetailView.as_view(),
        name="api_lesson_detail",
    ),
    # Enrollments
    path(
        "enrollments/",
        api_views.EnrollmentListCreateView.as_view(),
        name="api_enrollment_list",
    ),
    path(
        "enrollments/<int:pk>/",
        api_views.EnrollmentDetailView.as_view(),
        name="api_enrollment_detail",
    ),
    # Current user
    path("me/", api_views.MeView.as_view(), name="api_me"),
    # Payments (read-only)
    path("payments/", api_views.PaymentListCreateView.as_view(), name="api_payment_list"),
    path(
        "payments/<int:pk>/",
        api_views.PaymentDetailView.as_view(),
        name="api_payment_detail",
    ),
]
