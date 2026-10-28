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

        The view only sends course and student, so validate against attrs
        after the course has been resolved.
        """
        course = attrs.get("course")
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            if course and course.price > 0:
                raise serializers.ValidationError(
                    "This is a paid course — complete payment through Stripe checkout."
                )
        return attrs


class CourseDetailSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the public course detail view."""

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
        read_only_fields = fields
