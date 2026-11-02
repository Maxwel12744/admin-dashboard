"""Due-date reminders: 'Due soon' (next 24 hours) and 'Overdue' (last 7 days)."""
from datetime import timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .models import Notification, Task

SOON_HOURS = 24      # remind this long before the due date
OVERDUE_DAYS = 7     # stop reminding once a task is this long overdue


def create_due_reminders(user=None):
    """Create any missing reminders. Pass a user to check only their tasks.

    A task with no assignee reminds the project owner. Each reminder is created
    once: the message includes the due date, so editing the date sends a new one.
    Returns how many notifications were created.
    """
    now = timezone.now()
    soon = Q(due_date__gt=now, due_date__lte=now + timedelta(hours=SOON_HOURS))
    late = Q(due_date__lte=now, due_date__gte=now - timedelta(days=OVERDUE_DAYS))
    tasks = Task.objects.filter(is_done=False).filter(soon | late).select_related("assignee", "project__owner")
    if user is not None:
        tasks = tasks.filter(Q(assignee=user) | Q(assignee__isnull=True, project__owner=user))

    items = []
    for task in tasks:
        who = task.assignee or task.project.owner
        when = timezone.localtime(task.due_date).strftime("%b %d, %H:%M")
        if task.due_date > now:
            message = f"Due soon: “{task.title}” is due {when}"
        else:
            message = f"Overdue: “{task.title}” was due {when}"
        items.append((who, task, message))
    if not items:
        return 0

    existing = set(
        Notification.objects.filter(
            user__in={who for who, _, _ in items},
            message__in=[message for _, _, message in items],
        ).values_list("user_id", "message")
    )
    new = [
        Notification(user=who, message=message, link=reverse("task_detail", args=[task.pk]))
        for who, task, message in items
        if (who.id, message) not in existing
    ]
    Notification.objects.bulk_create(new)
    return len(new)