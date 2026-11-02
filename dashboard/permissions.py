"""Who can see and change what. Every view uses these helpers."""
from django.db.models import Q

from .models import Milestone, Project, Task


def visible_projects(user):
    """Projects you own, or where a task is assigned to you. Superusers see all."""
    if user.is_superuser:
        return Project.objects.all()
    return Project.objects.filter(Q(owner=user) | Q(tasks__assignee=user)).distinct()


def owned_projects(user):
    """Projects you may edit, delete and add tasks or milestones to."""
    if user.is_superuser:
        return Project.objects.all()
    return Project.objects.filter(owner=user)


def visible_tasks(user):
    return Task.objects.filter(project__in=visible_projects(user))


def owned_tasks(user):
    return Task.objects.filter(project__in=owned_projects(user))


def toggleable_tasks(user):
    """The owner and the assignee can mark a task done or reopen it."""
    if user.is_superuser:
        return Task.objects.all()
    return Task.objects.filter(Q(project__owner=user) | Q(assignee=user))


def owned_milestones(user):
    return Milestone.objects.filter(project__in=owned_projects(user))


def can_manage_project(user, project):
    return user.is_superuser or project.owner_id == user.id