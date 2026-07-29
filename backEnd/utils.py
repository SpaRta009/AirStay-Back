# backEnd/utils.py

from .models import Notification


def create_notification(user, notif_type, title, message, property_obj=None, booking_obj=None):
    """
    Crée une notification pour un utilisateur.
    """

    notification = Notification.objects.create(
        user=user,
        type=notif_type,
        title=title,
        message=message,
        property=property_obj,
        booking=booking_obj,
        is_read=False
    )

    return notification