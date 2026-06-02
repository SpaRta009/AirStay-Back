from .models import Category, Property, City, Booking, User, PropertyImage
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer


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

        url = obj.image.url

        # Cloudinary
        if url.startswith("http"):
            return url

        # Local dev
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

    # image principale
    image = serializers.SerializerMethodField()

    # images supplémentaires
    images = PropertyImageSerializer(
        many=True,
        read_only=True
    )

    def get_image(self, obj):
        if not obj.image:
            return None

        url = obj.image.url

        # Cloudinary
        if url.startswith("http"):
            return url

        # Local dev
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
            'image',        # image principale
            'images',       # images supplémentaires
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
            overlapping = Booking.objects.filter(
                property=prop,
                check_in__lt=check_out,
                check_out__gt=check_in,
                status__in=['pending', 'confirmed', 'paid'],
            )

            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)

            if overlapping.exists():
                raise serializers.ValidationError(
                    "This property is already booked for the selected dates."
                )

        return data