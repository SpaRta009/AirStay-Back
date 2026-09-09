from django.contrib.gis import admin
from .models import (
    Category,
    Notification,
    Property,
    City,
    Booking,
    User,
    PropertyImage,
    Wishlist,
    Amenity,
    Review,
    SubscriptionPlan,
    Subscription,
    CreditBatch,
    CreditTransaction,
    Conversation,
    Message,
)
# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'created_at']
    search_fields = ['category_name']

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'phone_number', 'has_profile_image']
    search_fields = ['username', 'email', 'phone_number']
    list_filter = ['role']

    def has_profile_image(self, obj):
        return bool(obj.profile_image)
    has_profile_image.boolean = True
    has_profile_image.short_description = 'Photo'

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

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    list_filter = ['type', 'is_read', 'created_at']

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'icon', 'is_custom', 'created_at']
    search_fields = ['name']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'property', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['property__property_name', 'user__username', 'comment']

# ============================================================

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['plan_type', 'credits', 'price_da']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'started_at', 'is_paid']
    list_filter = ['plan', 'is_paid']

@admin.register(CreditBatch)
class CreditBatchAdmin(admin.ModelAdmin):
    list_display = ['user', 'remaining', 'amount', 'purchased_at', 'expires_at']
    list_filter = ['expires_at']

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'amount', 'property', 'created_at']
    list_filter = ['action', 'created_at']

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ['sender', 'text', 'is_read', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_a', 'user_b', 'property', 'created_at', 'updated_at']
    search_fields = [
        'user_a__username',
        'user_a__email',
        'user_b__username',
        'user_b__email',
        'property__property_name',
    ]
    list_filter = ['created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user_a', 'user_b', 'property']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'text_preview', 'is_read', 'created_at']
    search_fields = ['conversation__id', 'sender__username', 'sender__email', 'text']
    list_filter = ['is_read', 'created_at']
    readonly_fields = ['created_at']
    autocomplete_fields = ['conversation', 'sender']

    @admin.display(description='Message')
    def text_preview(self, obj):
        return obj.text[:80]

