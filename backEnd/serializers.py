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

    # read : {"pk": 1, "name": "Alger"}
    city = CitySimpleSerializer(read_only=True)

    # write : accepte un city ID
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True,
        required=False,
    )

    # ✅ FIX IMAGES
    # Cloudinary → URL absolue https:// déjà correcte (obj.image.url retourne l'URL Cloudinary)
    # Local dev  → URL relative, on la rend absolue via request
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if not obj.image:
            return None

        url = obj.image.url  # Cloudinary : "https://res.cloudinary.com/..."
                              # Local      : "/media/property_images/photo.jpg"

        # Si c'est déjà une URL absolue (Cloudinary), on la retourne directement
        if url.startswith('http'):
            return url

        # Sinon (local dev), on la rend absolue avec la request
        request = self.context.get('request')
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