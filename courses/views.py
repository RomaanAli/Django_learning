from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.permissions import InstructorRequiredMixin

from .forms import CourseForm, LessonForm
from .models import Course, Enrollment, Lesson


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
        context["can_manage"] = course.is_managed_by(self.request.user)
        context["is_instructor"] = (
            self.request.user.is_authenticated
            and self.request.user.is_instructor
        )
        return context


class EnrollCourseView(LoginRequiredMixin, View):
    """Enroll the logged-in student in a FREE course (no duplicate enrollments).

    Paid courses (``price > 0``) are routed to the Stripe checkout instead —
    the student must pay before the enrollment is created (via webhook).
    """

    def _enroll(self, request, pk):
        course = get_object_or_404(
            Course.objects.filter(is_published=True), pk=pk
        )
        if not request.user.is_student:
            messages.error(request, "Instructors cannot enroll in courses.")
            return redirect("course_detail", pk=course.pk)
        if course.price > 0:
            messages.info(
                request,
                f'"{course.title}" is a paid course — please complete payment '
                "to enroll.",
            )
            return redirect("payments:confirm", course_id=course.pk)
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
        return self._enroll(request, pk)

    def post(self, request, pk):
        return self._enroll(request, pk)


class InstructorCourseListView(InstructorRequiredMixin, ListView):
    """List the courses the signed-in instructor manages."""

    model = Course
    template_name = "courses/instructor_course_list.html"
    context_object_name = "courses"

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Course.objects.select_related("instructor").all()
        return Course.objects.filter(instructor=user).select_related("instructor")


class InstructorCourseCreateView(InstructorRequiredMixin, View):
    """Let an instructor create a new course (unpublished until they publish)."""

    template_name = "courses/instructor_course_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CourseForm()})

    def post(self, request):
        form = CourseForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        course = form.save(commit=False)
        course.instructor = request.user
        course.is_published = False
        course.save()

        messages.success(request, f'"{course.title}" was created as a draft.')
        return redirect("instructor_course_edit", pk=course.pk)


class InstructorCourseEditView(InstructorRequiredMixin, View):
    """Edit a course — only by the instructor who owns it (or an admin)."""

    template_name = "courses/instructor_course_form.html"

    def _get_course(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        if not course.is_managed_by(request.user):
            messages.error(request, "You do not manage this course.")
            return None
        return course

    def get(self, request, pk):
        course = self._get_course(request, pk)
        if course is None:
            return redirect("instructor_course_list")
        return render(
            request,
            self.template_name,
            {"form": CourseForm(instance=course), "course": course},
        )

    def post(self, request, pk):
        course = self._get_course(request, pk)
        if course is None:
            return redirect("instructor_course_list")

        form = CourseForm(request.POST, instance=course)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "course": course},
            )

        form.save()
        messages.success(request, "The course was updated.")
        return redirect("instructor_course_edit", pk=course.pk)


class InstructorCoursePublishView(InstructorRequiredMixin, View):
    """Publish or unpublish one of the instructor's courses."""

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        if not course.is_managed_by(request.user):
            messages.error(request, "You do not manage this course.")
            return redirect("instructor_course_list")

        course.is_published = not course.is_published
        course.save(update_fields=["is_published"])
        if course.is_published:
            messages.success(request, f'"{course.title}" is now published.')
        else:
            messages.info(request, f'"{course.title}" was unpublished.')
        return redirect("instructor_course_edit", pk=course.pk)


class InstructorLessonCreateView(InstructorRequiredMixin, View):
    """Add a lesson to one of the instructor's courses."""

    template_name = "courses/instructor_lesson_form.html"

    def _get_course(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        if not course.is_managed_by(request.user):
            messages.error(request, "You do not manage this course.")
            return None
        return course

    def get(self, request, pk):
        course = self._get_course(request, pk)
        if course is None:
            return redirect("instructor_course_list")
        next_order = (course.lessons.order_by("-order").first().order + 1) if course.lessons.exists() else 1
        return render(
            request,
            self.template_name,
            {"form": LessonForm(initial={"order": next_order}), "course": course},
        )

    def post(self, request, pk):
        course = self._get_course(request, pk)
        if course is None:
            return redirect("instructor_course_list")

        form = LessonForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "course": course},
            )

        lesson = form.save(commit=False)
        lesson.course = course
        lesson.save()

        messages.success(request, f'Lesson "{lesson.title}" was added.')
        return redirect("instructor_course_edit", pk=course.pk)


class InstructorLessonEditView(InstructorRequiredMixin, View):
    """Edit or delete a lesson of one of the instructor's courses."""

    template_name = "courses/instructor_lesson_form.html"

    def _get_lesson(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        if not lesson.course.is_managed_by(request.user):
            messages.error(request, "You do not manage this lesson.")
            return None, None
        return lesson, lesson.course

    def get(self, request, pk):
        lesson, course = self._get_lesson(request, pk)
        if lesson is None:
            return redirect("instructor_course_list")
        return render(
            request,
            self.template_name,
            {"form": LessonForm(instance=lesson), "course": course, "lesson": lesson},
        )

    def post(self, request, pk):
        lesson, course = self._get_lesson(request, pk)
        if lesson is None:
            return redirect("instructor_course_list")

        if request.POST.get("action") == "delete":
            lesson.delete()
            messages.success(request, "The lesson was deleted.")
            return redirect("instructor_course_edit", pk=course.pk)

        form = LessonForm(request.POST, instance=lesson)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "course": course, "lesson": lesson},
            )

        form.save()
        messages.success(request, "The lesson was updated.")
        return redirect("instructor_course_edit", pk=course.pk)