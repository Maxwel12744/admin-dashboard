from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from .models import Project
from .models import Milestone
from .models import Task

CATEGORIES = (
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("mobile", "Mobile"),
    ("devops", "DevOps"),
)

class Notification(models.Model):
  """Alerts users when important actions happen (e.g., task assignment or deadline reminders)."""

  # Relationship: The user who receives the notification
  user = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      related_name="notifications",
  )

  message = models.CharField(
      max_length=255
  )  # Short text describing the event
  link = models.CharField(
      max_length=500, blank=True, null=True
  )  # Optional destination link when clicked
  is_read = models.BooleanField(
      default=False
  )  # Tracks whether the user has viewed the notification
  created_at = models.DateTimeField(
      auto_now_add=True
  )  # When the alert was generated

  class Meta:
    # Order by newest first so unread/recent alerts show up at the top
    ordering = ["-created_at"]

  def __str__(self):
    status_text = "Read" if self.is_read else "Unread"
    return f"Notification for {self.user.username} - {status_text}"
class Profile(models.Model):
  user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
  avatar = models.ImageField(upload_to="avatars/", blank=True)

  def __str__(self):
    return f"Profile of {self.user.username}"