from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Booking)
def on_booking_saved(sender, instance, created, **kwargs):
    try:
        from .utils import create_notification

        if created:
            create_notification(
                user=instance.property.owner,
                notif_type='booking_request',
                title=f'New booking request from {instance.user.username}',
                message=(
                    f'{instance.user.username} wants to book {instance.property.property_name} '
                    f'from {instance.check_in} to {instance.check_out}.'
                ),
                property_obj=instance.property,
                booking_obj=instance,
            )
            create_notification(
                user=instance.user,
                notif_type='booking_confirmed',
                title='Booking request sent!',
                message=(
                    f'Your request for {instance.property.property_name} '
                    f'from {instance.check_in} to {instance.check_out} '
                    f'has been sent. Waiting for host confirmation.'
                ),
                property_obj=instance.property,
                booking_obj=instance,
            )
    except Exception as e:
        logger.error(f"[Signal] Notification error: {e}", exc_info=True)