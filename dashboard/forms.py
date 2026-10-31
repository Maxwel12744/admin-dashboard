from django import forms
from django.contrib.auth import get_user_model

from .models import Project, Task


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = (
            "title",
            "description",
            "status",
            "start_date",
            "end_date",
            "created_by",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            "project",
            "milestone",
            "title",
            "description",
            "status",
            "priority",
            "assigned_to",
            "due_date",
        )
        widgets = {
            "due_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }