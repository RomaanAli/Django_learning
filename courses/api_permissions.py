from rest_framework import permissions


class IsInstructor(permissions.BasePermission):
    """Allow approved instructors and admins only (can_teach is True)."""

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return getattr(user, "can_teach", False)


class IsCourseOwner(permissions.BasePermission):
    """Object-level permission that reuses the model's own ownership logic,
    requiring that the user is authorized to teach (can_teach).
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not getattr(user, "can_teach", False):
            return False
        course_pk = getattr(view, "kwargs", {}).get("course_pk")
        if course_pk is None:
            return True
        from .models import Course

        course = Course.objects.filter(pk=course_pk).first()
        if course is None:
            return False
        return course.is_managed_by(user)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not getattr(user, "can_teach", False):
            return False
        if hasattr(obj, "is_managed_by"):
            return obj.is_managed_by(user)
        course = getattr(obj, "course", None)
        if course is not None and hasattr(course, "is_managed_by"):
            return course.is_managed_by(user)
        return False
