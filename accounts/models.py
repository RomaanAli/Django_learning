from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class User(AbstractUser):

    ROLE_STUDENT = "student"
    ROLE_INSTRUCTOR = "instructor"
    ROLE_ADMIN = "admin"


    ROLE_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_INSTRUCTOR, "Instructor"),
        (ROLE_ADMIN, "Admin"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        verbose_name="role",
    )
    is_approved_instructor = models.BooleanField(
        default=False,
        verbose_name="approved instructor",
        help_text="Designates whether this instructor has been approved to teach courses.",
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    @property
    def is_instructor(self) -> bool:
        """True when this user may manage courses."""
        return self.role == self.ROLE_INSTRUCTOR

    @property
    def is_admin(self) -> bool:
        """True when this user has platform-wide admin rights."""
        return self.role == self.ROLE_ADMIN

    @property
    def is_student(self) -> bool:
        """True when this user is an ordinary learner."""
        return self.role == self.ROLE_STUDENT

    @property
    def can_teach(self) -> bool:
        """True when this user has verified permissions to create and manage courses."""
        return self.is_admin or (self.is_instructor and self.is_approved_instructor)


class Profile(models.Model):
    """Extra profile fields for a user, shared by the whole site."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    age = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Your age in years.",
    )
    contact = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number or other contact detail.",
    )

    def __str__(self):
        return f"{self.user.username}\'s profile"


class EmailVerification(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification",
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the current OTP was generated (updated on every resend).",
    )
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    @property
    def is_expired(self) -> bool:
        """True once the 5-minute lifetime has passed."""
        return timezone.now() >= self.expires_at

    def __str__(self):
        state = "verified" if self.is_verified else "pending"
        return f"{self.user.username} - {state}"


class InstructorDocument(models.Model):

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_DENIED = "denied"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_DENIED, "Denied"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_document",
        verbose_name="user",
    )
    file = models.FileField(
        upload_to="instructor_documents/",
        verbose_name="document",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="status",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_documents",
        verbose_name="approved by",
    )
    review_note = models.TextField(
        blank=True,
        verbose_name="review note",
        help_text="Reason for denial or reviewer notes shown to the instructor.",
    )

    class Meta:
        verbose_name = "instructor document"
        verbose_name_plural = "instructor documents"

    @property
    def is_approved(self) -> bool:
        """True once an admin has approved this document."""
        return self.status == self.STATUS_APPROVED

    @property
    def is_pending(self) -> bool:
        """True while the document is still waiting for review."""
        return self.status == self.STATUS_PENDING

    def _save_stamped(self, update_fields) -> None:
        """Save only ``update_fields``, or everything for a brand new row."""
        if self.pk:
            self.save(update_fields=list(update_fields))
        else:
            self.save()

    def approve(self, reviewer=None) -> bool:
        with transaction.atomic():
            if self.status == self.STATUS_APPROVED and self.approved_at and self.user.is_approved_instructor:
                return False

            self.status = self.STATUS_APPROVED
            self.approved_at = self.approved_at or timezone.now()
            self.approved_by = reviewer or self.approved_by
            self.review_note = ""
            self._save_stamped(("status", "approved_at", "approved_by", "review_note"))

            user = self.user
            update_fields = ["is_approved_instructor"]
            if user.role == user.ROLE_STUDENT:
                user.role = user.ROLE_INSTRUCTOR
                update_fields.append("role")
            user.is_approved_instructor = True
            user.save(update_fields=update_fields)
            return True

    def deny(self, reviewer=None, reason="") -> bool:
        with transaction.atomic():
            reason_str = (reason or "").strip()
            if self.status == self.STATUS_DENIED and not self.user.is_approved_instructor and self.review_note == reason_str:
                return False

            self.status = self.STATUS_DENIED
            self.approved_at = None
            self.approved_by = None
            if reason_str:
                self.review_note = reason_str
            self._save_stamped(("status", "approved_at", "approved_by", "review_note"))

            user = self.user
            if user.is_approved_instructor:
                user.is_approved_instructor = False
                user.save(update_fields=["is_approved_instructor"])
            return True

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):

    if created and not kwargs.get("raw", False):
        Profile.objects.get_or_create(user=instance)
