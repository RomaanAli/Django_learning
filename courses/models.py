from django.conf import settings
from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    """Links a student to one course.

    The unique constraint on (student, course) guarantees a student can
    never enroll in the same course more than once.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student} is enrolled in {self.course}"
