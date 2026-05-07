from .models import Property, Category, City, User
from .serializers import CategorySerializer, CitySerializer, PropertySerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
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
class PropertyList(generics.ListCreateAPIView):
    queryset = Property.objects.filter(active=True)
    serializer_class = PropertySerializer
    name = 'properties-list'
    permission_classes = [IsAuthenticatedOrReadOnly]


class PropertyDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.filter(active=True)
    serializer_class = PropertySerializer
    name = 'properties-detail'


# ---- Cities ----
class CityList(generics.ListAPIView):
    serializer_class = CitySerializer
    name = "cities-list"

    def get_queryset(self):
        qs = City.objects.all()
        property_id = self.request.query_params.get("propertyid")
        search = self.request.query_params.get("search")

        if property_id:
            prop = get_object_or_404(Property, pk=property_id)
            return City.objects.annotate(
                distance=Distance("point_geom", prop.point_geom)
            ).order_by("distance")[:3]

        if search:
            return qs.filter(city_name__icontains=search)

        return qs[:10]


# ---- Auth ----
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data

    # ✅ FIX 1 : Vérifier les champs obligatoires manuellement pour un message clair
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if not data.get(field):
            return Response({'error': f'Le champ "{field}" est obligatoire.'}, status=400)

    try:
        # ✅ FIX 2 : phone vide ("") converti en None pour respecter unique=True
        raw_phone = data.get('phone', '')
        phone_value = raw_phone.strip() if raw_phone else None
        phone_value = phone_value if phone_value else None

        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('firstName', ''),
            last_name=data.get('lastName', ''),
            phone_number=phone_value,
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
                'phone': user.phone_number or '',
            }
        }, status=201)

    except Exception as e:
        # ✅ FIX 3 : Message d'erreur plus lisible
        error_msg = str(e)
        # Cas username déjà pris
        if 'username' in error_msg and 'already exists' in error_msg:
            return Response({'error': 'Ce nom d\'utilisateur est déjà utilisé.'}, status=400)
        # Cas email déjà pris (si tu ajoutes unique sur email plus tard)
        if 'email' in error_msg and 'already exists' in error_msg:
            return Response({'error': 'Cet email est déjà utilisé.'}, status=400)
        # Cas téléphone déjà pris
        if 'phone_number' in error_msg and 'already exists' in error_msg:
            return Response({'error': 'Ce numéro de téléphone est déjà utilisé.'}, status=400)
        return Response({'error': error_msg}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    # ✅ FIX 4 : Vérification des champs vides
    if not email or not password:
        return Response({'error': 'Email et mot de passe sont obligatoires.'}, status=400)

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
                    'phone': user.phone_number or '',
                }
            })
        return Response({'error': 'Mot de passe incorrect.'}, status=400)

    except User.DoesNotExist:
        return Response({'error': 'Aucun compte trouvé avec cet email.'}, status=400)