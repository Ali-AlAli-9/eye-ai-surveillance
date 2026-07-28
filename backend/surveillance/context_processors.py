import logging
from django.core.cache import cache
from .models import Alert

logger = logging.getLogger("audit")


def alert_count(request):
    result = {"unread_count": 0}
    if not request.user.is_authenticated:
        return result
    try:
        count = cache.get("unread_alert_count")
        if count is None:
            count = Alert.objects.filter(is_read=False).count()
            cache.set("unread_alert_count", count, 300)
        result["unread_count"] = count
    except Exception as e:
        logger.warning(f"[CTX] Failed to fetch unread count: {e}")
    return result
