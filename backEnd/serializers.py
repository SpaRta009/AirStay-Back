from .models import Category, Property, City
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer


# ── City simple (imbriqué dans Property) ──
class CitySimpleSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='city_name', read_only=True)

    class Meta:
        model = City
        fields = ('pk', 'name')


# ── Category ──
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


# ── Property ──
class PropertySerializer(GeoFeatureModelSerializer):

    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field='category_name'
    )

    # read : retourne {"pk": 1, "name": "Alger"}
    city = CitySimpleSerializer(read_only=True)

    # write : accepte un city ID
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True,
        required=False,
    )

    # ✅ FIX IMAGES : URL absolue HTTPS
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        if request:
            url = request.build_absolute_uri(obj.image.url)
            # Force HTTPS — Railway est derrière un proxy, build_absolute_uri
            # peut retourner http:// même avec SECURE_PROXY_SSL_HEADER
            return url.replace('http://', 'https://')
        # Fallback sans request : construire l'URL manuellement
        from django.conf import settings as django_settings
        base = 'https://web-production-26d8d.up.railway.app'
        return f"{base}{obj.image.url}"

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
            'active',
            'owner',
            'city',
            'city_id',
        )


# ── City GeoJSON complet (pour /cities/) ──
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