from rest_framework import permissions


class IsInstructor(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.is_instructor or user.is_admin


class IsCourseOwner(permissions.BasePermission):
    """Object-level permission that reuses the model's own ownership logic.

    For a Course the check is obj.is_managed_by(request.user); for a Lesson
    it delegates to the parent course's check.  This keeps the ownership rule
    in exactly one place and never re-implements it.
    """

    message = "You do not have permission to perform this action."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if hasattr(obj, "is_managed_by"):
            return obj.is_managed_by(user)
        # Fallback: if the object is_managed_by method, try going through
        # a parent course if the object is a Lesson.
        course = getattr(obj, "course", None)
        if course is not None and hasattr(course, "is_managed_by"):
            return course.is_managed_by(user)
        return False
