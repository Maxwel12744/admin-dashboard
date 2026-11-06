from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from .models import Project
from .models import Milestone
from .models import Task
from .models import Comment
from django import forms
CATEGORIES = (
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("mobile", "Mobile"),
    ("devops", "DevOps"),
)

