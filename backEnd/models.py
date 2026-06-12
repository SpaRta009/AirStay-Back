import os
import uuid
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError
from django.utils.text import slugify  # ✅ Importé pour nettoyer les noms de fichiers


# ✅ Nouvelle fonction pour nettoyer et sécuriser le nom des images
def upload_property_image_path(instance, filename):
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name)
    if not safe_name:
        safe_name = "property_photo"

    # Truncate to 40 chars so the full path stays well under the DB column limit:
    # "property_images/" (16) + name (40) + "_" + uuid (8) + ext (5) = ~70 chars max
    safe_name = safe_name[:40]

    unique_id = uuid.uuid4().hex[:8]
    return f"property_images/{safe_name}_{unique_id}{ext}"


class User(AbstractUser):
    second_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=[('guest', 'Guest'), ('host', 'Host')],
        default='guest'
    )
    # Superhost status is set manually by admins (e.g. via Django admin).
    # It is NEVER derived from listing order or any client-visible heuristic.
    is_superhost = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username


class Category(models.Model):
    category_name = models.CharField(max_length=50, help_text='House')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.category_name


class Property(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    city = models.ForeignKey('City', on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    property_name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    max_guests = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    # ✅ Modifié pour utiliser la fonction de nettoyage automatique
    image = models.ImageField(upload_to=upload_property_image_path, blank=True, null=True, max_length=200)
    active = models.BooleanField(default=True)
    point_geom = gis_models.PointField()

    class Meta:
        verbose_name_plural = 'Properties'

    def __str__(self):
        return self.property_name


class City(models.Model):
    city_name = models.CharField(max_length=50)
    point_geom = gis_models.PointField()

    def __str__(self):
        return self.city_name


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('canceled', 'Canceled'),
            ('completed', 'Completed'),
            ('paid', 'Paid')
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Bookings'
        indexes = [
            models.Index(fields=['check_in', 'check_out']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        nights = (self.check_out - self.check_in).days
        self.total_price = nights * self.property.price_per_night
        super().save(*args, **kwargs)

    def clean(self):
        if self.check_out <= self.check_in:
            raise ValidationError("Check-out must be after check-in")
        nights = (self.check_out - self.check_in).days
        if nights <= 0:
            raise ValidationError("Invalid booking duration")

        overlapping = Booking.objects.filter(
            property=self.property,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
            status__in=['confirmed', 'paid'],
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError("This property is already booked for these dates")


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    # ✅ Modifié pour utiliser la fonction de nettoyage automatique
    image = models.ImageField(upload_to=upload_property_image_path, max_length=200)

    class Meta:
        verbose_name_plural = 'Property Images'

    def __str__(self):
        return f"{self.property.property_name} - Image"


# ✅ NOUVEAU : Wishlist stockée en base de données
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Wishlists'
        # Un utilisateur ne peut pas sauvegarder la même propriété deux fois
        unique_together = ('user', 'property')

    def __str__(self):
        return f"{self.user.username} → {self.property.property_name}"
    

class Notification(models.Model):
    NOTIF_TYPES = [
        ('booking_request',   'Booking Request'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_canceled',  'Booking Canceled'),
        ('booking_completed', 'Booking Completed'),
        ('booking_expired',   'Booking Expired'),
        ('checkin_reminder',  'Check-in Reminder'),
        ('checkout_reminder', 'Checkout Reminder'),
        ('booking_paid',      'Booking Paid'),
    ]
 
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type         = models.CharField(max_length=30, choices=NOTIF_TYPES)
    title        = models.CharField(max_length=120)
    message      = models.TextField()
    property     = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    booking      = models.ForeignKey(Booking,  on_delete=models.SET_NULL, null=True, blank=True)
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
 
    def __str__(self):
        return f"{self.user.username} — {self.type}"