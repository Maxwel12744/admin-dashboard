from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


CATEGORIES = (
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("mobile", "Mobile"),
    ("devops", "DevOps"),
)


class Project(models.Model):
  """Represents a major project being managed in the dashboard.

  Acts as the parent container for tasks, milestones, and discussions.
  """

  class Status(models.TextChoices):
    PLANNING = "planning", "Planning"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"

  STATUS_CHOICES = Status.choices

  # Basic Project Information
  name = models.CharField(max_length=200)
  description = models.TextField(
      blank=True, null=True
  )  # Optional details about the project
  category = models.CharField(max_length=20, choices=CATEGORIES, default="frontend")
  status = models.CharField(
      max_length=20, choices=Status.choices, default=Status.PLANNING
  )

  # Timeline fields
  start_date = models.DateField()
  deadline = models.DateField(
      blank=True, null=True
  )  # Optional deadline/end date
  manual_progress = models.PositiveSmallIntegerField(default=0)
  repo_url = models.URLField(blank=True)
  live_url = models.URLField(blank=True)

  # Relationship: Tracks which user created/owns this project.
  # settings.AUTH_USER_MODEL points safely to your active User model.
  # on_delete=models.CASCADE means if the user is deleted, their projects are also deleted.
  owner = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      related_name="projects",
  )

  # Automated timestamps
  created_at = models.DateTimeField(
      auto_now_add=True
  )  # Set automatically on creation
  updated_at = models.DateTimeField(
      auto_now=True
  )  # Updated automatically on every save

  class Meta:
    # Default sorting: Show newest projects first when querying
    ordering = ["-created_at"]

  @property
  def progress(self):
    task_counts = self.tasks.aggregate(
        total=Count("id"), completed=Count("id", filter=Q(is_done=True))
    )
    if task_counts["total"]:
      return round(task_counts["completed"] * 100 / task_counts["total"])
    return 100 if self.status == self.Status.COMPLETED else self.manual_progress

  def __str__(self):
    # Returns the project title in the Django Admin or shell
    return self.name


class Milestone(models.Model):
  """Represents major phases, deadlines, or checkpoints within a specific project."""

  # Relationship: Linked to a Project. If the project is deleted, its milestones go with it.
  project = models.ForeignKey(
      Project, on_delete=models.CASCADE, related_name="milestones"
  )

  title = models.CharField(max_length=200)
  due_date = models.DateField()
  is_completed = models.BooleanField(
      default=False
  )  # Tracks if the milestone is achieved

  class Meta:
    # Sort milestones chronologically by their due date
    ordering = ["due_date"]

  def __str__(self):
    return f"{self.project.name} - {self.title}"


class Task(models.Model):
  """Individual to-dos or actionable assignments belonging to a project."""

  STATUS_CHOICES = [
      ("todo", "To Do"),
      ("in_progress", "In Progress"),
      ("done", "Done"),
  ]

  PRIORITY_CHOICES = [
      ("low", "Low"),
      ("medium", "Medium"),
      ("high", "High"),
  ]

  # Relationships
  project = models.ForeignKey(
      Project, on_delete=models.CASCADE, related_name="tasks"
  )

  # Optional link to a milestone (SET_NULL keeps the task if the milestone is deleted)
  milestone = models.ForeignKey(
      Milestone,
      on_delete=models.SET_NULL,
      blank=True,
      null=True,
      related_name="tasks",
  )

  # Task Details
  title = models.CharField(max_length=200)
  description = models.TextField(blank=True, null=True)
  category = models.CharField(max_length=20, choices=CATEGORIES, default="frontend")
  status = models.CharField(
      max_length=20, choices=STATUS_CHOICES, default="todo"
  )
  priority = models.CharField(
      max_length=20, choices=PRIORITY_CHOICES, default="medium"
  )

  # Relationship: The team member assigned to handle this task (can be unassigned/null)
  assignee = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.SET_NULL,
      blank=True,
      null=True,
      related_name="assigned_tasks",
  )

  # Deadline and creation tracking
  due_date = models.DateTimeField()
  created_at = models.DateTimeField(auto_now_add=True)
  is_done = models.BooleanField(default=False)
  completed_at = models.DateTimeField(blank=True, null=True)

  class Meta:
    # Order tasks by upcoming due dates
    ordering = ["due_date"]

  def save(self, *args, **kwargs):
    if self.is_done:
      self.status = "done"
      if self.completed_at is None:
        self.completed_at = timezone.now()
    else:
      if self.status == "done":
        self.status = "todo"
      self.completed_at = None
    super().save(*args, **kwargs)

  def __str__(self):
    # Returns the title alongside its human-readable status (e.g., "Fix Bug (In Progress)")
    return f"{self.title} ({self.get_status_display()})"


class Comment(models.Model):
  """Allows users to leave progress updates, notes, or discuss specific tasks."""

  # Relationship: Belongs to a task; deleting the task deletes its comments
  task = models.ForeignKey(
      Task, on_delete=models.CASCADE, related_name="comments"
  )

  # Relationship: Tracks who wrote the comment
  author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

  content = models.TextField()  # The body of the comment
  created_at = models.DateTimeField(
      auto_now_add=True
  )  # When the comment was posted

  class Meta:
    # Sort comments chronologically from oldest to newest (conversation flow)
    ordering = ["created_at"]

  def __str__(self):
      return f"Comment by {self.author.username} on {self.task.title}"


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
