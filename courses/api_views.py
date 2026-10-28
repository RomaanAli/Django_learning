from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response

from courses.models import Course, Enrollment, Lesson
from .api_permissions import IsCourseOwner, IsInstructor
from .serializers import (
    CourseSerializer,
    CourseDetailSerializer,
    EnrollmentSerializer,
    LessonSerializer,
)


class CourseListCreateView(generics.ListCreateAPIView):
    """List published courses (AllowAny) or create a new course (IsInstructor).

    Queryset scope: published courses only, plus the request user's own
    courses if authenticated (so draft courses are visible to their owner on
    the API).  Uses select_related("instructor") to avoid N+1 queries.  Search
    and ordering are provided by DRF's built-in filters.
    """

    serializer_class = CourseSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["price", "title"]
    ordering = ["price"]

    def get_permissions(self):
        # Public reads: AllowAny (DRF global default is IsAuthenticated, so we
        # must explicitly override for GET).
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        # Writes: only instructors and admins, with superusers bypassing the
        # mixin.
        return [IsInstructor()]

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.filter(is_published=True)
        if user.is_authenticated:
            qs = qs | Course.objects.filter(instructor=user)
        return (
            qs.distinct()
            .select_related("instructor")
            .annotate(
                lesson_count=Count("lessons", distinct=True),
                enrollment_count=Count("enrollments", distinct=True),
            )
        )

    def perform_create(self, serializer):
        # The serializer's instructor field is read-only, so the view must
        # set ownership explicitly — otherwise creation failed / had no owner.
        serializer.save(instructor=self.request.user)


class CourseDetailView(generics.RetrieveUpdateAPIView):
    """Public read + owner write.

    GET: anonymous and ordinary users see published courses only; the
    authenticated user additionally sees their own draft courses.
    PUT/PATCH: IsCourseOwner.
    No DELETE — web UI has no course delete, so the API must not add one.
    instructor and is_published stay read-only.
    """

    serializer_class = CourseDetailSerializer
    http_method_names = ["get", "put", "patch"]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [IsCourseOwner()]

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.filter(is_published=True)
        if user.is_authenticated and not user.is_superuser:
            qs = qs | Course.objects.filter(instructor=user)
        return qs.select_related("instructor")


class InstructorCourseListView(generics.ListAPIView):
    """List courses the signed-in instructor manages.

    Admins/superusers see all courses (drafts included); instructors see only
    their own.  Uses select_related("instructor").
    """

    serializer_class = CourseSerializer

    def get_permissions(self):
        return [IsInstructor()]

    def get_queryset(self):
        if self.request.user.is_admin:
            qs = Course.objects.all()
        else:
            qs = Course.objects.filter(instructor=self.request.user)
        return qs.select_related("instructor").annotate(
            lesson_count=Count("lessons", distinct=True),
            enrollment_count=Count("enrollments", distinct=True),
        )


class LessonListCreateView(generics.ListCreateAPIView):
    """List lessons of a course or create a new lesson.

    GET: IsAuthenticated + enrollment/owner rule.  Only the enrolled student or
    the owning instructor/admin may list lessons; everything else gets a clear
    403.
    POST: IsCourseOwner on the parent course.
    """

    serializer_class = LessonSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsCourseOwner()]

    def get_queryset(self):
        return Lesson.objects.filter(course_id=self.kwargs["course_pk"]).order_by(
            "order"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["course_pk"] = self.kwargs["course_pk"]
        return context

    def list(self, request, *args, **kwargs):
        course = get_object_or_404(Course, pk=self.kwargs["course_pk"])
        if request.user.is_authenticated and not (
            course.is_managed_by(request.user)
            or Enrollment.objects.filter(
                student=request.user, course=course
            ).exists()
        ):
            return Response(
                {"detail": "Enroll to view lessons"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs["course_pk"])


class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Read/update/delete a single lesson.

    GET uses the lesson-read rule.  PUT/PATCH/DELETE use IsCourseOwner on the
    parent course.  The queryset filters course_id=course_pk so a lesson ID
    cannot be reused to peek into another course.
    """

    serializer_class = LessonSerializer
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return Lesson.objects.filter(course_id=self.kwargs["course_pk"])

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsCourseOwner()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["course_pk"] = self.kwargs["course_pk"]
        return context

    def retrieve(self, request, *args, **kwargs):
        # Mirror list(): a lesson is visible only to an enrolled student
        # or the course owner/admin. Previously any authenticated user
        # could fetch a lesson by id, bypassing enrolment entirely.
        course = get_object_or_404(Course, pk=self.kwargs["course_pk"])
        if not (
            course.is_managed_by(request.user)
            or Enrollment.objects.filter(
                student=request.user, course=course
            ).exists()
        ):
            return Response(
                {"detail": "Enroll to view lessons"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)


class EnrollmentListCreateView(generics.ListCreateAPIView):
    """List the requesting user's enrollments or create a new one.

    GET: IsAuthenticated, only the requesting user's own enrollments, newest
    first.
    POST: IsAuthenticated.  The view sets student=request.user.  The serializer
    rejects paid courses (Stripe message) and duplicate enrollments (400 via
    the model's UniqueConstraint).
    """

    serializer_class = EnrollmentSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return (
            Enrollment.objects.filter(student=self.request.user)
            .select_related("course")
            .order_by("-enrolled_at")
        )

    def perform_create(self, serializer):
        # Mirror the web flow: instructors/admins cannot enrol in courses.
        if not self.request.user.is_student:
            raise PermissionDenied("Instructors cannot enroll in courses.")
        serializer.save(student=self.request.user)


class EnrollmentDetailView(generics.RetrieveAPIView):
    """Retrieve a single enrollment.

    Queryset restricted to the requesting user's own enrollments.  Another
    user's enrollment returns 404 (never 403 with details).
    """

    serializer_class = EnrollmentSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user).select_related(
            "course"
        )


class MeView(generics.RetrieveAPIView):
    """Serialize the current user with the exact legacy response shape.

    GET /api/me/ must return exactly {"id", "username", "email",
    "email_verified"}.  A dedicated four-field serializer is used because the
    full UserSerializer would add first_name, last_name and role, which would
    break the hard contract.
    """

    permission_classes = [permissions.IsAuthenticated]
    queryset = None  # set in the view below

    def get_serializer_class(self):
        from accounts.serializers import MeUserSerializer

        return MeUserSerializer

    def get_queryset(self):
        from accounts.models import User

        return User.objects.none()

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @staticmethod
    def _email_verified(user):
        from accounts.models import EmailVerification

        try:
            # The reverse OneToOne relation is ``email_verification``.
            return user.email_verification.is_verified
        except EmailVerification.DoesNotExist:
            return False


class PaymentListCreateView(generics.ListAPIView):
    """Read-only list of the requesting user's payments, newest first."""

    serializer_class = None  # set in the view below

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        from payments.serializers import PaymentSerializer

        return PaymentSerializer

    def get_queryset(self):
        return (
            self.request.user.payments.select_related("course")
            .order_by("-created_at")
        )


class PaymentDetailView(generics.RetrieveAPIView):
    """Read-only detail of a single payment.

    Queryset restricted to the requesting user's payments.
    Another user's payment returns 404.
    """

    serializer_class = None

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        from payments.serializers import PaymentSerializer

        return PaymentSerializer

    def get_queryset(self):
        return self.request.user.payments.select_related("course")
