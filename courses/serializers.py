from rest_framework import serializers

from .models import Course, Enrollment, Lesson


class InstructorMiniSerializer(serializers.Serializer):
    """Read-only nested instructor representation.

    Only id and username are exposed. Instructor emails are never leaked in
    course responses.
    """

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)


class CourseSerializer(serializers.ModelSerializer):
    """Course serializer exposed through the API.

    instructor and is_published are read-only. Publishing stays web-only;
    even if a client sends is_published:true it is ignored. lesson_count is a
    read-only SerializerMethodField that delegates to the model's reverse
    relation.
    """

    instructor = InstructorMiniSerializer(read_only=True)
    is_published = serializers.ReadOnlyField()
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "price",
            "is_published",
            "instructor",
            "lesson_count",
        ]
        read_only_fields = [
            "id",
            "is_published",
            "instructor",
            "lesson_count",
        ]

    def get_lesson_count(self, obj):
        # Prefer the annotated count (see API list querysets) so a list
        # response does not issue one query per course; fall back to the
        # relation count for single objects without the annotation.
        annotated = getattr(obj, "lesson_count", None)
        if annotated is not None:
            return annotated
        return obj.lessons.count()

    def validate_price(self, value):
        """Mirror CourseForm's min_value = 0."""
        if value < 0:
            raise serializers.ValidationError("Price must be >= 0.")
        return value


class LessonSerializer(serializers.ModelSerializer):
    """Lesson serializer.

    The parent course is always supplied by the view from the URL; the client
    can never set it.
    """

    course = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "content",
            "order",
            "course",
        ]
        read_only_fields = ["id", "course"]


class EnrollmentSerializer(serializers.ModelSerializer):
    """Enrollment serializer.

    student is read-only and set by the view. course is a primary key whose
    queryset is restricted to published courses (an unpublished course gives
    a clean 400 on creation). enrolled_at is read-only and auto-set.
    """

    student = serializers.IntegerField(read_only=True)
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(is_published=True),
        source="course_id",
    )
    enrolled_at = serializers.ReadOnlyField()

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student",
            "course",
            "enrolled_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "enrolled_at",
        ]

    def validate(self, attrs):
        """Paid courses are never created via the API.

        The ``course`` field uses ``source="course_id"``, so the resolved
        Course instance arrives under the ``course_id`` key in validated
        data — the old ``attrs.get("course")`` lookup was always None and
        the paid-course check never fired.
        """
        course = attrs.get("course_id") or attrs.get("course")
        if course and course.price > 0:
            raise serializers.ValidationError(
                "This is a paid course — complete payment through Stripe checkout."
            )
        return attrs


class CourseDetailSerializer(serializers.ModelSerializer):
    """Serializer for the course detail view.

    GET keeps the lightweight public shape, but PUT/PATCH must be able to
    change title/description/price — the old ``read_only_fields = fields``
    made every update a no-op. id/is_published/instructor stay read-only:
    publishing stays web-only and ownership is set by the view, never the
    client.
    """

    instructor = InstructorMiniSerializer(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "price",
            "is_published",
            "instructor",
        ]
        read_only_fields = [
            "id",
            "is_published",
            "instructor",
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price must be >= 0.")
        return value
