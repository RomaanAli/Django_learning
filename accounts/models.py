from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class User(AbstractUser):
    """Custom user model for the E-learning project.
    Starts identical to Django''s built-in User and gains role-based
    access control (student / instructor / admin).
    """
    role = models.CharField(
        max_length=20,
        choices=[
            ("student", "Student"),
            ("instructor", "Instructor"),
            ("admin", "Admin"),
        ],
        default="student",
        verbose_name="role",
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"


class Profile(models.Model):

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
        return f"{self.user.username}'s profile"


class EmailVerification(models.Model):
    """One 6-digit OTP row per user, used to verify a new account''s email.

    A single row per user (OneToOne) means "resend OTP" simply replaces the
    stored code, which also invalidates the previous code.
    """

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


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):

    if created and not kwargs.get("raw", False):
        Profile.objects.get_or_create(user=instance)
