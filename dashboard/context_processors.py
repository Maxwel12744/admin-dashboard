def notifications(request):
    """Gives every template the unread count and the latest notifications."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    qs = user.notifications.order_by("-id")
    return {
        "unread_count": qs.filter(is_read=False).count(),
        "recent_notifications": qs[:6],
    }
