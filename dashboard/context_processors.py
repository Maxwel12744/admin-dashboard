import time

from .reminders import create_due_reminders

CHECK_EVERY_SECONDS = 600  # look for new reminders at most every 10 minutes per person


def notifications(request):
    """Gives every template the unread count and the latest notifications."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    now = int(time.time())
    last = request.session.get("reminders_checked", 0)
    if now - last >= CHECK_EVERY_SECONDS:
        create_due_reminders(user)
        request.session["reminders_checked"] = now

    qs = user.notifications.order_by("-id")
    return {
        "unread_count": qs.filter(is_read=False).count(),
        "recent_notifications": qs[:6],
    }