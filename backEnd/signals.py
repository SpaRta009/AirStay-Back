from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from .utils import create_notification  # adapte selon ton projet

@receiver(post_save, sender=Booking)
def on_booking_created(sender, instance, created, **kwargs):
    if created:
        create_notification(
            instance.property.owner,
            'booking_request',
            f'New booking request from {instance.user.username}',
            f'{instance.user.username} wants to book {instance.property.property_name} '
            f'({instance.check_in} → {instance.check_out}).',
            instance.property,
            instance,
        )