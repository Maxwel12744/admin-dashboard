import time

from .models import Profile
from .reminders import create_due_reminders

CHECK_EVERY_SECONDS = 600  # look for new reminders at most every 10 minutes per person


def notifications(request):
    """Gives every template the unread count, the latest notifications and the avatar."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    now = int(time.time())
    last = request.session.get("reminders_checked", 0)
    if now - last >= CHECK_EVERY_SECONDS:
        create_due_reminders(user)
        request.session["reminders_checked"] = now

    profile = Profile.objects.filter(user=user).exclude(avatar="").first()
    qs = user.notifications.order_by("-id")
    return {
        "unread_count": qs.filter(is_read=False).count(),
        "recent_notifications": qs[:6],
        "avatar_url": profile.avatar.url if profile else "",
    }