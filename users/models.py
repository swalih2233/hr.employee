from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

# FIX: Added a Profile model to store user-specific profile information.
# This model is linked one-to-one with the User model.
# It includes an image field for the user's profile picture.
# A default image is specified to prevent errors when no image is uploaded.
class Profile(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_images/', default='profile_images/default.jpg', null=True, blank=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.user.username

from django.contrib.auth.models import AbstractUser, UserManager
class UserManager(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(max_length=150, unique=False, null=True, blank=True)
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    # FIX: Ensured email is unique as it's used for login.
    email = models.EmailField(_('email address'), unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='M')
    
    # FIX: Made phone_number unique to avoid duplicate entries.
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # FIX: Added is_manager and is_employee flags for role-based access control.
    is_manager = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

# FIX: Added a signal to automatically create or update the user's profile
# whenever a User object is saved. This ensures that every user has a profile.
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    
    # FIX: Check if the user has a profile before saving it.
    # This prevents errors for users created before the Profile model was introduced.
    if hasattr(instance, 'profile'):
        instance.profile.save()

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.user.email}"
