from django.contrib import admin

from .models import Course, Enrollment, Lesson


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "is_published")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "enrolled_at")
    list_filter = ("course",)
    search_fields = ("student__username", "course__title")
