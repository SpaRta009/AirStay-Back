import os
import uuid
from django.db import models, transaction
from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError
from django.utils.text import slugify  # ✅ Importé pour nettoyer les noms de fichiers
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date
from dateutil.relativedelta import relativedelta 


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


def upload_profile_image_path(instance, filename):
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name)
    if not safe_name:
        safe_name = "avatar"
    safe_name = safe_name[:40]

    unique_id = uuid.uuid4().hex[:8]
    return f"profile_images/{safe_name}_{unique_id}{ext}"


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
    profile_image = models.ImageField(
        upload_to=upload_profile_image_path, blank=True, null=True, max_length=200
    )
    # ✅ NEW — needed for a real profile page (about section / contact info)
    bio = models.TextField(blank=True, default="")
    location = models.CharField(max_length=100, blank=True, default="")

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
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    amenities = models.ManyToManyField('Amenity', blank=True, related_name='properties')
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


# ✅ NOUVEAU : Amenities (Wifi, Piscine, Parking, etc.)
# Les amenities "standard" sont créées par l'admin / via fixture.
# Un hôte peut aussi proposer un amenity personnalisé depuis le formulaire
# (created_by_user=True) — il reste utilisable par tout le monde ensuite,
# ça évite la duplication si plusieurs hôtes proposent la même chose.
class Amenity(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=30, blank=True, default="check")  # clé d'icône front-end
    is_custom = models.BooleanField(default=False)  # True = ajouté par un hôte, pas dans la liste standard
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Amenities'
        ordering = ['name']

    def __str__(self):
        return self.name

class Review(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # Garantit qu'un utilisateur ne peut laisser qu'un seul avis par propriété
        unique_together = ('property', 'user')

    def __str__(self):
        return f"Avis de {self.user.username} sur {self.property.property_name} ({self.rating}/5)"

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

def default_expiry():
    """Un lot de crédits achetés ce mois-ci expire à la fin du mois suivant."""
    today = date.today()
    first_of_next_next_month = (today.replace(day=1) + relativedelta(months=2))
    return first_of_next_next_month  # ex: achat en janvier -> expire le 1er mars


class SubscriptionPlan(models.Model):
    """Catalogue statique des offres (monthly / yearly)."""
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
    PLAN_CHOICES = [(MONTHLY, 'Monthly'), (YEARLY, 'Yearly')]

    plan_type = models.CharField(max_length=10, choices=PLAN_CHOICES, unique=True)
    credits = models.PositiveIntegerField()      # 70 ou 840
    price_da = models.DecimalField(max_digits=10, decimal_places=2)  # 1000 ou 9000

    def __str__(self):
        return f"{self.plan_type} - {self.credits} credits - {self.price_da} DA"


class Subscription(models.Model):
    """Historique des abonnements souscrits par un utilisateur (à but d'audit / affichage)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    started_at = models.DateTimeField(auto_now_add=True)
    # simple trace du paiement — à brancher sur ton vrai système de paiement
    is_paid = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.plan_type} ({self.started_at.date()})"


class CreditBatch(models.Model):
    """
    Un lot de crédits achetés à une date donnée.
    Consommé en FIFO. Expire automatiquement.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_batches')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE,
                                      related_name='batches', null=True, blank=True)
    amount = models.PositiveIntegerField()          # crédits initiaux du lot
    remaining = models.PositiveIntegerField()        # crédits restants dans ce lot
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(default=default_expiry)  # 1er jour du mois où ça expire

    class Meta:
        ordering = ['purchased_at']  # FIFO : le plus ancien d'abord

    def is_expired(self):
        return date.today() >= self.expires_at

    def __str__(self):
        return f"{self.user.username} - {self.remaining}/{self.amount} (exp {self.expires_at})"


class CreditTransaction(models.Model):
    """Journal de chaque mouvement de crédit (achat / consommation / expiration)."""
    ACTION_CHOICES = [
        ('purchase', 'Purchase'),
        ('property_create', 'Property Create'),
        ('property_edit', 'Property Edit'),
        ('expired', 'Expired'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    amount = models.IntegerField()  # positif = crédit, négatif = débit
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} {self.action} {self.amount}"