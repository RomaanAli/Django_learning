from django import forms

from .models import Course, Lesson


class CourseForm(forms.ModelForm):
    """Create/update a course owned by the signed-in instructor."""

    class Meta:
        model = Course
        fields = ["title", "description", "price"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price"].min_value = 0


class LessonForm(forms.ModelForm):
    """Create/update a lesson inside a course."""

    class Meta:
        model = Lesson
        fields = ["title", "content", "order"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 6}),
        }
