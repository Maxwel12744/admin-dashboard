
from django.contrib import admin
from .models import Comment, Milestone, Notification, Project, Task

# Register your models here so they appear in the Django Admin
admin.site.register(Project)
admin.site.register(Milestone)
admin.site.register(Task)
admin.site.register(Comment)
admin.site.register(Notification)