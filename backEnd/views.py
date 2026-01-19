from .models import Property, Category, City
from .serializers import CategorySerializer, CitySerializer, PropertySerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from django.http import Http404
from django.contrib.gis.db.models.functions import Distance
from django.shortcuts import get_object_or_404

# ---- Categories ----
class CategoryList(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    name = 'category-list'

class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    name = 'category-detail'

# ---- Properties ----
class PropertyList(generics.ListAPIView):
    queryset = Property.objects.filter(active=True)
    serializer_class = PropertySerializer
    name = 'properties-list'

class PropertyDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.filter(active=True)
    serializer_class = PropertySerializer
    name = 'properties-detail'

# ---- Cities ----
class CityList(generics.ListAPIView):
    serializer_class = CitySerializer
    name = "cities-list"

    def get_queryset(self):
        property_id = self.request.query_params.get("propertyid")

        if property_id is None:
            raise Http404("propertyid query parameter is required.")
        
        selected_property_geom = get_object_or_404(Property, pk=property_id).point_geom

        nearest_cities = City.objects.annotate(
            distance=Distance("point_geom", selected_property_geom)
        ).order_by("distance")[:3]

        return nearest_cities
