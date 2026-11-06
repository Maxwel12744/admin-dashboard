from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.files.uploadedfile import UploadedFile

from .models import Comment, Milestone, Profile, Project, Task
from .permissions import owned_milestones, owned_projects

User = get_user_model()

MAX_AVATAR_BYTES = 2 * 1024 * 1024  # Vercel rejects uploads over 4.5 MB anyway
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only superusers may pick a different owner; everyone else owns what they create.
        if user is not None and not user.is_superuser:
            self.fields.pop("owner")


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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # "Done" is controlled by the is_done checkbox (Task.save sets the status)
        self.fields["status"].choices = [c for c in Task.STATUS_CHOICES if c[0] != "done"]
        self.fields["assignee"].queryset = User.objects.filter(is_active=True)
        if user is not None:
            self.fields["project"].queryset = owned_projects(user)
            self.fields["milestone"].queryset = owned_milestones(user)

    def clean(self):
        data = super().clean()
        project, milestone = data.get("project"), data.get("milestone")
        if project and milestone and milestone.project_id != project.pk:
            self.add_error("milestone", "This milestone belongs to a different project.")
        return data


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ["title", "due_date", "is_completed"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        labels = {"content": "Add a comment"}
        widgets = {"content": forms.Textarea(attrs={"rows": 3})}


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class AvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["avatar"]

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        # Only check a file that was just uploaded. An existing picture is a stored
        # file, and asking cloud storage for its size is not supported.
        if isinstance(avatar, UploadedFile):
            if avatar.size > MAX_AVATAR_BYTES:
                raise forms.ValidationError("The picture must be 2 MB or smaller.")
            content_type = getattr(avatar, "content_type", "")
            if content_type not in ALLOWED_IMAGE_TYPES:
                raise forms.ValidationError("Use a PNG, JPG, WEBP or GIF picture.")
        return avatar


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Used for password reset emails.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email