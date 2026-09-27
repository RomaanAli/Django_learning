from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Profile(models.Model):
    """Extra per-student information stored alongside the auth User."""

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
    """One 6-digit OTP row per user, used to verify a new account's email.

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
    """Automatically create a Profile whenever a new user is created.

    The `raw` guard skips this during fixture loads (e.g. ``loaddata``), where
    the Profile rows come from the fixture itself. Without it, importing users
    from a backup would first auto-create a Profile for each user and then
    collide with the Profile record stored in the fixture (unique constraint
    on user).
    """
    if created and not kwargs.get("raw", False):
        Profile.objects.get_or_create(user=instance)
