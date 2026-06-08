from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from .utils import create_notification

@receiver(post_save, sender=Booking)
def on_booking_saved(sender, instance, created, **kwargs):
    if created:
        # Notification au HOST — nouvelle demande
        create_notification(
            instance.property.owner,
            'booking_request',
            f'New booking request from {instance.user.username}',
            f'{instance.user.username} wants to book {instance.property.property_name} '
            f'({instance.check_in} → {instance.check_out}).',
            instance.property,
            instance,
        )
        # Notification au GUEST — confirmation de réception
        create_notification(
            instance.user,
            'booking_confirmed',
            f'Booking request sent!',
            f'Your request for {instance.property.property_name} '
            f'({instance.check_in} → {instance.check_out}) has been sent to the host.',
            instance.property,
            instance,
        )
    else:
        # Booking mis à jour — notifier le guest du nouveau statut
        status = instance.status
        if status == 'confirmed':
            create_notification(
                instance.user,
                'booking_confirmed',
                'Booking confirmed! 🎉',
                f'Your booking at {instance.property.property_name} '
                f'({instance.check_in} → {instance.check_out}) has been confirmed.',
                instance.property,
                instance,
            )
        elif status == 'canceled':
            create_notification(
                instance.user,
                'booking_canceled',
                'Booking canceled',
                f'Your booking at {instance.property.property_name} '
                f'({instance.check_in} → {instance.check_out}) was canceled.',
                instance.property,
                instance,
            )