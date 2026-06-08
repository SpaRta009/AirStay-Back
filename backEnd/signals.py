from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from .utils import create_notification


@receiver(post_save, sender=Booking)
def on_booking_saved(sender, instance, created, **kwargs):

    if created:
        # ── Notifier le HOST : nouvelle demande ──
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
        # ── Notifier le GUEST : demande envoyée ──
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

    else:
        status = instance.status

        if status == 'confirmed':
            # ── Notifier le GUEST : confirmé ──
            create_notification(
                user=instance.user,
                notif_type='booking_confirmed',
                title='Booking confirmed! 🎉',
                message=(
                    f'Your booking at {instance.property.property_name} '
                    f'from {instance.check_in} to {instance.check_out} '
                    f'has been confirmed by the host.'
                ),
                property_obj=instance.property,
                booking_obj=instance,
            )

        elif status == 'canceled':
            # ── Notifier le GUEST : annulé ──
            create_notification(
                user=instance.user,
                notif_type='booking_canceled',
                title='Booking canceled',
                message=(
                    f'Your booking at {instance.property.property_name} '
                    f'from {instance.check_in} to {instance.check_out} '
                    f'has been canceled.'
                ),
                property_obj=instance.property,
                booking_obj=instance,
            )
            # ── Notifier le HOST aussi ──
            create_notification(
                user=instance.property.owner,
                notif_type='booking_canceled',
                title='Booking canceled',
                message=(
                    f'The booking from {instance.user.username} '
                    f'({instance.check_in} to {instance.check_out}) '
                    f'has been canceled.'
                ),
                property_obj=instance.property,
                booking_obj=instance,
            )

        elif status == 'completed':
            create_notification(
                user=instance.user,
                notif_type='booking_completed',
                title='Stay completed 🎉',
                message=(
                    f'Your stay at {instance.property.property_name} is complete. '
                    f'Thank you for using AirStay!'
                ),
                property_obj=instance.property,
                booking_obj=instance,
            )