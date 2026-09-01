from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class StudentRegistrationForm(UserCreationForm):
    """Our one form: lets a new student create an account."""

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "password1", "password2"]