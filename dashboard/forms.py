from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from .models import Project
from .models import Milestone
from .models import Task
from .models import Comment

CATEGORIES = (
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("mobile", "Mobile"),
    ("devops", "DevOps"),
)


class Profile(models.Model):
  user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
  avatar = models.ImageField(upload_to="avatars/", blank=True)

  def __str__(self):
    return f"Profile of {self.user.username}"