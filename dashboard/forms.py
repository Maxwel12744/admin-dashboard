from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from .models import Project
from .models import Milestone
from .models import Task
from .models import Comment
from django import forms
from .models import Profile
CATEGORIES = (
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("mobile", "Mobile"),
    ("devops", "DevOps"),
)

class AvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["avatar"]

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            # Enforce a 2MB limit matching your template
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image file size must not exceed 2MB.")
        return avatar