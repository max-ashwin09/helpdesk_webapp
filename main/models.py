from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

# Custom user model with additional phone field
# class CustomUser(AbstractUser):
#     phone = models.CharField(max_length=15, unique=True)
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    phone = models.CharField(
        max_length=15,
        unique=True,
        null=True,     # NULL allow (SQLite me multiple NULL allowed hote hain)
        blank=True     # admin form me optional rahega; superuser ke liye hum REQUIRED_FIELDS use karenge
    )

    # agar username hi login field hai, to phone ko REQUIRED_FIELDS me include karo
    REQUIRED_FIELDS = ["email", "phone"]  # createsuperuser ab phone puchhega







# OTP model to store one-time password with expiry check
class OTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 60

# Question model used for asking questions in helpdesk
class Question(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    body = models.TextField()
    tags = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    file = models.FileField(upload_to='uploads/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return self.title

# For multiple file upload
class QuestionFile(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

# File Upload Model

class UploadedFile(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class Comment(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    file = models.FileField(upload_to="comment_files/", null=True, blank=True)  # File upload for comments
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} commented: {self.content}"



# Profile model to store user profile information
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from django.contrib.auth.models import User

User = get_user_model()

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)  
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png')

    def __str__(self):
        return f"{self.user.username} Profile"

# 🔥 Signal: user create/update → profile auto-create/update
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()

