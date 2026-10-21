from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import InstructorDocument, Profile

User = get_user_model()

MAX_DOCUMENT_SIZE_MB = 5
ALLOWED_DOCUMENT_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg")
ALLOWED_DOCUMENT_CONTENT_TYPES = (
    "application/pdf",
    "image/png",
    "image/jpeg",
)


class StudentRegistrationForm(UserCreationForm):

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
        user.is_active = False
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


class InstructorDocumentForm(forms.ModelForm):
    """Upload form for the proof-of-qualification an instructor applies with."""

    class Meta:
        model = InstructorDocument
        fields = ["file"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"accept": ".pdf,.png,.jpg,.jpeg"}),
        }

    def clean_file(self):
        uploaded = self.cleaned_data["file"]

        name = (uploaded.name or "").lower()
        if not any(name.endswith(ext) for ext in ALLOWED_DOCUMENT_EXTENSIONS):
            raise forms.ValidationError(
                "Only PDF, PNG or JPG documents are accepted "
                f"({', '.join(ALLOWED_DOCUMENT_EXTENSIONS)})."
            )

        content_type = (uploaded.content_type or "").lower()
        if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
            raise forms.ValidationError(
                "That file type is not supported. Please upload a PDF, PNG or JPG."
            )

        max_bytes = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
        if uploaded.size > max_bytes:
            raise forms.ValidationError(
                f"The file is too large (max {MAX_DOCUMENT_SIZE_MB} MB)."
            )

        return uploaded
