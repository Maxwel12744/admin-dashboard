from django import forms
from django.contrib.auth import get_user_model

from .models import Project, Task

User = get_user_model()


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name", "description", "category", "status", "owner",
            "start_date", "deadline", "manual_progress", "repo_url", "live_url",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "deadline": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "project", "milestone", "title", "description", "category",
            "status", "priority", "assignee", "due_date", "is_done",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # "Done" is controlled by the is_done checkbox (Task.save sets the status)
        self.fields["status"].choices = [c for c in Task.STATUS_CHOICES if c[0] != "done"]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]