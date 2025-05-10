from django.db import models
from django.contrib.auth.models import AbstractUser

from .manager import UserManager
from django.core.validators import RegexValidator

from django.utils.timezone import now
from datetime import timedelta
from django.utils import timezone

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other')
)

MARITUL_STATUS_CHOICES = (
    ('SI', 'SINGILE'),
    ('MA', 'MARRIED'),
    ('OT', 'OTHER')
)
class User(AbstractUser):
    username = None  # Remove the username field
    email = models.EmailField(max_length=255, unique=True, 
                              error_messages={'unique': "Email already used"})
    employe_id = models.CharField(max_length=100, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=100, choices=GENDER_CHOICES, null=True, blank=True, default='O')
    maritul_status = models.CharField(max_length=200, null=True, blank=True, choices=MARITUL_STATUS_CHOICES, default='OT')
    phone_number = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 
                   "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")],
    )
    is_manager = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # No additional required fields

    objects = UserManager()  # Use the custom manager here

    class Meta:
        db_table = 'users_user'
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ["-id"]

    def __str__(self):
        return f"{self.email} ({self.employe_id})"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'users_otp'
        verbose_name = 'OTP'
        verbose_name_plural = 'OTPs'
        ordering = ["-id"]

    def is_expired(self):
        """Check if the OTP has expired (assuming expiration time is 10 minutes)."""
        return self.expires_at < timezone.now()

    def __str__(self):
        return f"OTP for {self.user.email}"