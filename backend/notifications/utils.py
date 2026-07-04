from .models import Notification


def create_notification(
    recipient,
    title,
    content,
    category='system',
    related_type=None,
    related_id=None
):
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        content=content,
        category=category,
        related_type=related_type,
        related_id=related_id
    )