from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError


class User(AbstractUser):
    second_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=[('guest', 'Guest'), ('host', 'Host')],
        default='guest'
    )

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
    image = models.ImageField(upload_to='property_images/', blank=True, null=True)
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

        # ✅ FIX: Only block overlap for confirmed or paid bookings.
        # Multiple guests can send pending requests for the same dates —
        # the host chooses who to confirm. Once confirmed/paid, it blocks others.
        overlapping = Booking.objects.filter(
            property=self.property,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
            status__in=['confirmed', 'paid'],  # removed 'pending'
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError("This property is already booked for these dates")


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/')

    class Meta:
        verbose_name_plural = 'Property Images'

    def __str__(self):
        return f"{self.property.property_name} - Image"