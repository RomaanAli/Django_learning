from django.shortcuts import get_object_or_404, render

from .models import Course


def course_list(request):
    courses = Course.objects.filter(is_published=True)
    return render(request, "courses/course_list.html", {"courses": courses})


def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    return render(request, "courses/course_detail.html", {"course": course})
