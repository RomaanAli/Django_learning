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
DANGEROUS_EXTENSIONS = {
    "exe", "bat", "cmd", "sh", "php", "py", "js", "html", "htm", "jar",
    "vbs", "scr", "dll", "com", "msi", "ps1", "app", "cgi"
}


def validate_instructor_document(uploaded):
    if not uploaded:
        raise forms.ValidationError("Please select a file to upload.")

    if uploaded.size == 0:
        raise forms.ValidationError("The uploaded file is empty.")

    max_bytes = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    if uploaded.size > max_bytes:
        raise forms.ValidationError(
            f"The file is too large (max {MAX_DOCUMENT_SIZE_MB} MB)."
        )

    name = (uploaded.name or "").lower()
    parts = name.split(".")
    if len(parts) < 2 or not any(name.endswith(ext) for ext in ALLOWED_DOCUMENT_EXTENSIONS):
        allowed_str = ", ".join(ALLOWED_DOCUMENT_EXTENSIONS)
        raise forms.ValidationError(
            f"Only PDF, PNG or JPG documents are accepted ({allowed_str})."
        )

    # Reject double extensions / dangerous embedded extensions e.g. file.exe.pdf, file.php.jpg
    if any(part in DANGEROUS_EXTENSIONS for part in parts[:-1]):
        raise forms.ValidationError(
            "Files with executable or script extensions are not allowed."
        )

    content_type = (getattr(uploaded, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise forms.ValidationError(
            "That file type is not supported. Please upload a PDF, PNG or JPG."
        )

    return uploaded



VALID_REGISTER_ROLES = (
    (User.ROLE_STUDENT, 'Student'),
    (User.ROLE_INSTRUCTOR, 'Instructor'),
)


class StudentRegistrationForm(UserCreationForm):
    role = forms.CharField(
        required=False,
        initial=User.ROLE_STUDENT,
        widget=forms.HiddenInput(),
    )
    document = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.png,.jpg,.jpeg'}),
        help_text=(
            "For instructors only. Upload a document that proves you can teach "
            "(PDF or image, max 5 MB). An admin will review it. You can log in "
            "while you wait, but you cannot create courses until you are approved."
        ),
    )

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'password1',
            'password2',
        ]

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            raise forms.ValidationError('Email is required.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email

    def clean_role(self):
        role = (self.cleaned_data.get('role') or '').strip().lower()
        if role not in dict(VALID_REGISTER_ROLES):
            role = User.ROLE_STUDENT
        return role

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role') or User.ROLE_STUDENT
        document = cleaned_data.get('document')

        if role == User.ROLE_INSTRUCTOR:
            if not document:
                self.add_error('document', 'Document is required for instructor registration.')
            else:
                try:
                    validate_instructor_document(document)
                except forms.ValidationError as err:
                    self.add_error('document', err)
        else:
            cleaned_data['document'] = None

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        user.role = self.cleaned_data.get('role') or User.ROLE_STUDENT
        user.is_approved_instructor = False
        if commit:
            user.save()
            document = self.cleaned_data.get('document')
            if user.role == User.ROLE_INSTRUCTOR and document:
                InstructorDocument.objects.create(
                    user=user,
                    file=document,
                    status=InstructorDocument.STATUS_PENDING,
                )
        return user


class UserEditForm(forms.ModelForm):
    '''Edits the basic auth-user fields shown on the profile page.'''

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        # Previously any user could save another user's email (or blank
        # it), breaking OTP/password-reset delivery for that account.
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            raise forms.ValidationError('Email is required.')
        if (
            User.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError('A user with that email already exists.')
        return email


class ProfileForm(forms.ModelForm):
    '''Edits the profile-specific fields (age, contact).'''

    class Meta:
        model = Profile
        fields = ['age', 'contact']


class InstructorDocumentForm(forms.ModelForm):
    '''Upload form for the proof-of-qualification an instructor applies with.'''

    class Meta:
        model = InstructorDocument
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'accept': '.pdf,.png,.jpg,.jpeg'}),
        }

    def clean_file(self):
        uploaded = self.cleaned_data.get('file')
        return validate_instructor_document(uploaded)
