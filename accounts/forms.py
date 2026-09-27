from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class StudentRegistrationForm(UserCreationForm):
    """Lets a new student create an INACTIVE account (a Profile is auto-created).

    The account only becomes active after the email OTP is verified, so a user
    cannot log in before confirming their email address.
    """

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  # awaits email verification
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """Edits the basic auth-user fields shown on the profile page."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class ProfileForm(forms.ModelForm):
    """Edits the profile-specific fields (age, contact)."""

    class Meta:
        model = Profile
        fields = ["age", "contact"]