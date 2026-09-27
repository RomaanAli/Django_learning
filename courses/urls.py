from django.urls import path
from . import views

urlpatterns = [
    path("", views.CourseListView.as_view(), name="course_list"),
    path("<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("<int:pk>/enroll/", views.EnrollCourseView.as_view(), name="enroll_course"),
]