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

    def __init__(self, *args, **kwargs):
        course = kwargs.pop("course", None)
        self.course = course
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.course_id:
            self.course = self.instance.course
        self.fields["order"].min_value = 1

    def clean_order(self):
        order = self.cleaned_data.get("order")
        if order is None:
            return order
        if self.course is None:
            return order
        qs = Lesson.objects.filter(course=self.course, order=order)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Another lesson in this course already has this order. Choose a different order."
            )
        return order

    class Meta:
        model = Lesson
        fields = ["title", "content", "order"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 6}),
        }