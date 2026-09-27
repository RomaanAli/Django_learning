from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from .models import Course, Enrollment


class CourseListView(ListView):
    """Show the list of published courses."""

    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    queryset = Course.objects.filter(is_published=True)


class CourseDetailView(DetailView):
    """Show a single course plus the visitor's enrollment status."""

    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        context["is_enrolled"] = (
            self.request.user.is_authenticated
            and course.enrollments.filter(student=self.request.user).exists()
        )
        return context


class EnrollCourseView(LoginRequiredMixin, View):
    """Enroll the logged-in student in a course (no duplicate enrollments)."""

    def _enroll(self, request, pk):
        course = get_object_or_404(
            Course.objects.filter(is_published=True), pk=pk
        )
        _, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
        )
        if created:
            messages.success(request, f'You are now enrolled in "{course.title}".')
        else:
            messages.info(request, f'You are already enrolled in "{course.title}".')
        return redirect("course_detail", pk=course.pk)

    def get(self, request, pk):
        # The original FBV accepted any HTTP method; keep GET working too.
        return self._enroll(request, pk)

    def post(self, request, pk):
        return self._enroll(request, pk)