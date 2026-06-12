from .models import Category, Notification, Property, City, Booking, User, PropertyImage
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer


# ─────────────────────────────────────────────────────────────────────────────
# Cloudinary URL normaliser
#
# Files are stored in Cloudinary with public IDs like:
#   media/property_images/foo_abc123
#
# django-cloudinary-storage builds the URL as:
#   https://res.cloudinary.com/<cloud>/image/upload/v1/media/property_images/foo_abc123
#
# That URL is correct. The only issue is that Cloudinary sometimes omits the
# file extension from the public ID, so the URL ends without ".jpg".
# Cloudinary returns a 404 for extension-less URLs; appending ".jpg" fixes it.
# ─────────────────────────────────────────────────────────────────────────────
def fix_cloudinary_url(url: str) -> str:
    if not url:
        return url

    # Append .jpg when the last path segment has no file extension
    last_segment = url.split("/")[-1].split("?")[0]  # strip query string
    if "res.cloudinary.com" in url and "." not in last_segment:
        url = f"{url}.jpg"

    return url


# ─────────────────────────────
# User
# ─────────────────────────────
class UserSerializer(serializers.ModelSerializer):
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
            'is_superhost',   # needed by the property card — never expose via index tricks
        )
        read_only_fields = fields


# ─────────────────────────────
# City simple (nested in Property)
# ─────────────────────────────
class CitySimpleSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='city_name', read_only=True)

    class Meta:
        model = City
        fields = ('pk', 'name')


# ─────────────────────────────
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

    images = PropertyImageSerializer(
        many=True,
        read_only=True
    )

    # Dans serializers.py

    def get_image(self, obj):
        image_field = obj.image
        if not image_field:
            first = obj.images.first()
            if first and first.image:
                image_field = first.image
            else:
                return None

        url = fix_cloudinary_url(image_field.url)

        if url.startswith("http"):
            return url

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)

        return url

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
            'created_at',
            'modified_at',
            'image',
            'images',
            'active',
            'owner',
            'city',
            'city_id',
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