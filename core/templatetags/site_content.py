"""Read-only template tags that surface real site data to templates.

Every query in this module is read-only (``count()`` and simple ``SELECT``
queries). Nothing is ever created, updated, or deleted, so loading these tags
cannot change backend state or database contents.
"""

from django import template

register = template.Library()


@register.simple_tag
def site_stats():
    """Return real catalog statistics used on the home page.

    Returns a dict with:
    * ``courses``     -- number of published courses
    * ``lessons``     -- number of lessons belonging to published courses
    * ``enrollments`` -- total number of course enrollments
    """
    from courses.models import Course, Enrollment, Lesson

    return {
        "courses": Course.objects.filter(is_published=True).count(),
        "lessons": Lesson.objects.filter(course__is_published=True).count(),
        "enrollments": Enrollment.objects.count(),
    }


@register.simple_tag
def featured_courses(limit=3):
    """Return up to ``limit`` published courses for the home page."""
    from courses.models import Course

    return Course.objects.filter(is_published=True).order_by("pk")[:limit]
