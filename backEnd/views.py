from .models import Property, Category, City, User
from .serializers import CategorySerializer, CitySerializer, PropertySerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
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

# ---- Auth ----
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data
    try:
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('firstName', ''),
            last_name=data.get('lastName', ''),
            phone_number=data['phone'],
            role=data.get('role', 'guest'),
        )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'phone': user.phone_number,
            }
        }, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    try:
        user_obj = User.objects.get(email=email)
        user = authenticate(username=user_obj.username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'phone': user.phone_number,
                }
            })
        return Response({'error': 'Invalid credentials'}, status=400)
    except User.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=400)