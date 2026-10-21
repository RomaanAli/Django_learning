from django.urls import path
from . import views

urlpatterns = [
    path("", views.CourseListView.as_view(), name="course_list"),
    path("<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("<int:pk>/enroll/", views.EnrollCourseView.as_view(), name="enroll_course"),
    path(
        "instructor/",
        views.InstructorCourseListView.as_view(),
        name="instructor_course_list",
    ),
    path(
        "instructor/new/",
        views.InstructorCourseCreateView.as_view(),
        name="instructor_course_create",
    ),
    path(
        "instructor/<int:pk>/edit/",
        views.InstructorCourseEditView.as_view(),
        name="instructor_course_edit",
    ),
    path(
        "instructor/<int:pk>/publish/",
        views.InstructorCoursePublishView.as_view(),
        name="instructor_course_publish",
    ),
    path(
        "instructor/<int:pk>/lessons/new/",
        views.InstructorLessonCreateView.as_view(),
        name="instructor_lesson_create",
    ),
    path(
        "instructor/lessons/<int:pk>/edit/",
        views.InstructorLessonEditView.as_view(),
        name="instructor_lesson_edit",
    ),
]