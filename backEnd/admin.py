from django.contrib.gis import admin
from .models import Category, Property, City, Booking, User, PropertyImage, Wishlist
# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'created_at']
    search_fields = ['category_name']

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'phone_number']
    search_fields = ['username', 'email', 'phone_number']
    list_filter = ['role']

class CustomGeoAdmin(admin.GISModelAdmin):
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 7,
            'default_lon': 3.0697,
            'default_lat': 36.7457,
        }
    }

@admin.register(Property)
class PropertyAdmin(CustomGeoAdmin):
    list_display = ['property_name', 'owner', 'city', 'category', 'price_per_night', 'max_guests', 'active']
    search_fields = ['property_name', 'owner__username', 'city__city_name']
    list_filter = ['city', 'category', 'active']
    
@admin.register(City)
class CityAdmin(CustomGeoAdmin):
    pass

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'property', 'check_in', 'check_out', 'status', 'total_price']
    search_fields = ['user__username', 'property__property_name']
    list_filter = ['status', 'created_at']
    readonly_fields = ['total_price', 'created_at', 'modified_at']

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ['property', 'image']
    search_fields = ['property__property_name']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'property', 'created_at']
    search_fields = ['user__username', 'property__property_name']
    list_filter = ['created_at']