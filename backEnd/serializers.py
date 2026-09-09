from .models import Category, Notification, Property, City, Booking, User, PropertyImage, Amenity, Review, SubscriptionPlan, Subscription, CreditBatch, CreditTransaction, Conversation, Message
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .credits_utils import get_balance


# ─────────────────────────────────────────────────────────────────────────────
# Cloudinary URL normaliser
#
# django-cloudinary-storage stores files with public IDs like:
#   media/property_images/foo_abc123
#
# It then builds the URL as:
#   https://res.cloudinary.com/<cloud>/image/upload/v1/media/property_images/foo_abc123
#
# The "v1/" token is a fake cache-buster injected by the library. Cloudinary
# only accepts a versioned URL if the file was actually assigned that version
# at upload time (which django-cloudinary-storage never does). So the "v1/"
# causes a 404 for every file.
#
# Fix: strip "/v1/" (and any "/vNNN/" version token) from the upload path.
# Also append ".jpg" when the public ID has no file extension, because
# Cloudinary returns a 404 for extension-less public IDs too.
# ─────────────────────────────────────────────────────────────────────────────
import re

def fix_cloudinary_url(url: str) -> str:
    """
    Fixes URLs produced by django-cloudinary-storage so they never expire.

    Problem 1 – Fake version token:
      django-cloudinary-storage emits /upload/v1/media/... but Cloudinary only
      accepts a versioned URL when the file was uploaded with that exact version
      (which the library never does). Result: 404. Fix: strip /vNNN/.

    Problem 2 – Missing file extension:
      When the original filename has no extension Cloudinary returns 404 for the
      bare URL. Fix: append .jpg.

    Problem 3 – Signed / expiring URLs (THE MAIN BUG):
      When Cloudinary is configured with CLOUDINARY_STORAGE = {'SECURE': True}
      or when sign_url=True is used anywhere, django-cloudinary-storage appends
      an auth signature + timestamp to every URL:
        ?_a=<signature>&timestamp=<unix_ts>
      or via the newer SDK:
        /s--<signature>--/
      These tokens expire after ~1 hour (free plan) or up to 24 hours depending
      on the account type. After expiry every image returns 404 — even though the
      file still exists on Cloudinary.

      Fix: strip ALL query parameters AND any inline signature segment (/s--...--/)
      from the URL to produce a permanent unsigned delivery URL. Unsigned URLs work
      as long as the resource is not restricted to "authenticated" access in the
      Cloudinary dashboard (the default for any file uploaded without special
      access_control is "public").

    Problem 4 – Authenticated delivery mode:
      If your Cloudinary account has "Strict Transformations" enabled or files were
      uploaded with access_type='authenticated', unsigned URLs will still 404.
      In that case set ACCESS_MODE = 'public' in your CLOUDINARY_STORAGE settings
      and re-upload files, or disable "Strict Transformations" in the dashboard.
    """
    if not url:
        return url

    if "res.cloudinary.com" not in url:
        return url

    # Step 1: strip the fake version token  /upload/v<digits>/  →  /upload/
    url = re.sub(r"/upload/v\d+/", "/upload/", url)

    # Step 2: strip inline signature segments like /s--AbCdEfGh--/
    # These are inserted by the Cloudinary SDK for signed transformations.
    url = re.sub(r"/s--[A-Za-z0-9_-]+--/", "/", url)

    # Step 3: strip ALL query-string parameters.
    # Signed URLs append ?_a=...&timestamp=... which expire after 1–24 hours.
    # Removing them yields a permanent unsigned delivery URL.
    path_part = url.split("?")[0]

    # Step 4: if the public ID has no file extension, Cloudinary returns 404.
    # Append .jpg — the correct extension for browser image uploads.
    has_ext = bool(re.search(
        r'\.(jpg|jpeg|png|webp|gif|avif|heic|bmp|tiff?)$',
        path_part,
        re.IGNORECASE,
    ))
    if not has_ext:
        path_part += ".jpg"

    # Step 5: inject f_auto,q_auto so Cloudinary auto-selects format + quality.
    # Only inject once, and only if no transformation is already present.
    if "/upload/" in path_part and "/upload/f_auto" not in path_part:
        path_part = path_part.replace("/upload/", "/upload/f_auto,q_auto/", 1)

    return path_part


# ─────────────────────────────
# User
# ─────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'role',
            'is_superhost',
            'profile_image',
            'bio',
            'location',
            'date_joined',
        )
        read_only_fields = fields

    def get_profile_image(self, obj):
        if not obj.profile_image:
            return None
        url = fix_cloudinary_url(obj.profile_image.url)
        if url.startswith("http"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


# ✅ NOUVEAU : sérialiseur dédié à la mise à jour du profil (PATCH /profile/update/)
# Séparé de UserSerializer (qui est entièrement read-only) pour ne jamais
# exposer accidentellement des champs sensibles (username, email, role, is_superhost...)
# à la modification par l'utilisateur lui-même.
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'bio', 'location')

    def validate_bio(self, value):
        if len(value) > 500:
            raise serializers.ValidationError("Bio must be 500 characters or fewer.")
        return value


# ─────────────────────────────
# City simple (nested in Property)
# ─────────────────────────────
class CitySimpleSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='city_name', read_only=True)

    class Meta:
        model = City
        fields = ('pk', 'name')


# # ─────────────────────────────
# PropertyImage
# ─────────────────────────────
class PropertyImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ('id', 'image')

    def get_image(self, obj):
        if not obj.image:
            return None
        url = fix_cloudinary_url(obj.image.url)
        if url.startswith("http"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


# ─────────────────────────────
# Category
# ─────────────────────────────
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


# ─────────────────────────────
# Amenity
# ─────────────────────────────
class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ('id', 'name', 'icon', 'is_custom')
        read_only_fields = ('is_custom',)

# ─────────────────────────────
# Review
# ─────────────────────────────
class ReviewSerializer(serializers.ModelSerializer):
    user_username = serializers.ReadOnlyField(source='user.username')
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Review
        fields = ['id', 'rating', 'comment', 'created_at', 'user_username']

# ─────────────────────────────
# Property
# ─────────────────────────────
class PropertySerializer(GeoFeatureModelSerializer):

    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field='category_name'
    )

    city = CitySimpleSerializer(read_only=True)

    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True,
        required=False,
    )

    owner = UserSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    images = PropertyImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    amenity_ids = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        source='amenities',
        many=True,
        write_only=True,
        required=False,
    )
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    def get_image(self, obj):
        # 🚨 FIX ULTIME : Si pas de cover, on renvoie null. Plus de fallback !
        if not obj.image:
            return None

        url = fix_cloudinary_url(obj.image.url)

        if url.startswith("http"):
            return url

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)

        return url
    
    def get_average_rating(self, obj):
        from django.db.models import Avg
        avg = obj.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else 0.0

    def get_review_count(self, obj):
        return obj.reviews.count()

    class Meta:
        model = Property
        geo_field = "point_geom"
        fields = (
            'pk',
            'category',
            'property_name',
            'description',
            'price_per_night',
            'max_guests',
            'bedrooms',
            'bathrooms',
            'amenities',
            'amenity_ids',
            'created_at',
            'modified_at',
            'image',
            'images',
            'active',
            'owner',
            'city',
            'city_id',
            'reviews',
            'average_rating',
            'review_count',
        )

# ─────────────────────────────
# City GeoJSON
# ─────────────────────────────
class CitySerializer(GeoFeatureModelSerializer):
    proximity = serializers.SerializerMethodField()

    def get_proximity(self, obj):
        if hasattr(obj, 'distance'):
            return obj.distance.km
        return None

    class Meta:
        model = City
        geo_field = "point_geom"
        fields = (
            "pk",
            "city_name",
            "proximity",
        )


# ─────────────────────────────
# Booking
# ─────────────────────────────
class BookingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Booking
        fields = (
            'id',
            'property',
            'check_in',
            'check_out',
            'total_price',
            'status',
            'created_at'
        )
        read_only_fields = (
            'total_price',
            'status',
            'created_at'
        )

    def validate(self, data):
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        prop = data.get('property')

        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError(
                "Check-out must be after check-in."
            )

        if check_in and check_out and prop:
            # ✅ FIX: Only block overlap for confirmed or paid bookings.
            # 'pending' bookings do NOT block new reservations — a booking
            # is only truly reserved once a host confirms it.
            overlapping = Booking.objects.filter(
                property=prop,
                check_in__lt=check_out,
                check_out__gt=check_in,
                status__in=['confirmed', 'paid'],  # removed 'pending'
            )

            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)

            if overlapping.exists():
                raise serializers.ValidationError(
                    "This property is already booked for the selected dates."
                )

        return data
    
class NotificationSerializer(serializers.ModelSerializer):
    property_id   = serializers.SerializerMethodField()
    property_name = serializers.SerializerMethodField()
    booking_id    = serializers.SerializerMethodField()
 
    class Meta:
        model  = Notification
        fields = (
            'id', 'type', 'title', 'message',
            'property_id', 'property_name', 'booking_id',
            'is_read', 'created_at',
        )
        read_only_fields = fields

    # On vérifie proprement si l'objet existe avant d'accéder à ses attributs
    def get_property_id(self, obj):
        return obj.property.pk if obj.property else None

    def get_property_name(self, obj):
        return obj.property.property_name if obj.property else None

    def get_booking_id(self, obj):
        return obj.booking.pk if obj.booking else None

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'plan_type', 'credits', 'price_da')


class CreditWalletSerializer(serializers.Serializer):
    """Non lié à un modèle : renvoie juste le solde courant + le détail des lots actifs."""
    balance = serializers.SerializerMethodField()
    batches = serializers.SerializerMethodField()

    def get_balance(self, user):
        return get_balance(user)

    def get_batches(self, user):
        from datetime import date
        qs = CreditBatch.objects.filter(user=user, remaining__gt=0, expires_at__gt=date.today())
        return [
            {'remaining': b.remaining, 'amount': b.amount, 'expires_at': b.expires_at}
            for b in qs
        ]


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = ('id', 'action', 'amount', 'property', 'created_at')


# ─────────────────────────────
# Chat
# ─────────────────────────────
class ChatUserSerializer(serializers.ModelSerializer):
    """Petite représentation d'un utilisateur, utilisée dans le contexte du chat."""
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'profile_image')

    def get_profile_image(self, obj):
        if not obj.profile_image:
            return None
        url = fix_cloudinary_url(obj.profile_image.url)
        if url.startswith("http"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url


class MessageSerializer(serializers.ModelSerializer):
    sender = ChatUserSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'conversation', 'sender', 'text', 'is_read', 'is_mine', 'created_at')
        read_only_fields = ('id', 'conversation', 'sender', 'is_read', 'is_mine', 'created_at')

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.sender_id == request.user.id)

    def validate_text(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError("Message cannot be empty.")
        if len(value) > 4000:
            raise serializers.ValidationError("Message is too long (max 4000 characters).")
        return value


class ConversationSerializer(serializers.ModelSerializer):
    """
    Représentation d'une conversation du point de vue de l'utilisateur courant :
    - `other_user` : l'interlocuteur
    - `property_id` / `property_name` : contexte optionnel (annonce concernée)
    - `last_message` : aperçu du dernier message
    - `unread_count` : nombre de messages non lus envoyés par l'autre utilisateur
    """
    other_user = serializers.SerializerMethodField()
    property_id = serializers.SerializerMethodField()
    property_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            'id', 'other_user', 'property_id', 'property_name',
            'last_message', 'unread_count', 'updated_at', 'created_at',
        )
        read_only_fields = fields

    def _current_user(self):
        request = self.context.get("request")
        return request.user if request else None

    def get_other_user(self, obj):
        user = self._current_user()
        other = obj.other_user(user) if user else obj.user_b
        return ChatUserSerializer(other, context=self.context).data

    def get_property_id(self, obj):
        return obj.property_id

    def get_property_name(self, obj):
        return obj.property.property_name if obj.property_id else None

    def get_last_message(self, obj):
        last = getattr(obj, 'last_message_obj', None)
        if last is None:
            last = obj.messages.order_by('-created_at').first()
        if not last:
            return None
        return {
            'text': last.text,
            'sender_id': last.sender_id,
            'created_at': last.created_at.isoformat(),
            'is_read': last.is_read,
        }

    def get_unread_count(self, obj):
        user = self._current_user()
        if not user:
            return 0
        count = getattr(obj, 'unread_count_val', None)
        if count is not None:
            return count
        return obj.messages.filter(is_read=False).exclude(sender=user).count()