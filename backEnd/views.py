from .models import Property, Category, City, User, Booking
from .serializers import CategorySerializer, CitySerializer, PropertySerializer, BookingSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.shortcuts import get_object_or_404


# ── Categories ──
class CategoryList(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    name = 'category-list'

class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    name = 'category-detail'


# ── Properties ──
class PropertyList(generics.ListCreateAPIView):
    queryset = Property.objects.filter(active=True)
    serializer_class = PropertySerializer
    name = 'properties-list'
    permission_classes = [IsAuthenticatedOrReadOnly]

    def create(self, request, *args, **kwargs):
        """
        ✅ FIX : override create pour gérer le FormData du frontend.
        Le frontend envoie :
          - category  → ID numérique (on résout par pk)
          - city      → ID numérique (on résout par pk)
          - lat / lng → coordonnées GPS séparées (on assemble en Point)
          - image     → fichier binaire
        """
        data = request.data

        # ── Résoudre la catégorie (ID ou nom) ──
        cat_val = data.get('category')
        if not cat_val:
            return Response({'error': 'category est requis.'}, status=400)
        try:
            category = Category.objects.get(pk=int(cat_val))
        except (ValueError, TypeError):
            try:
                category = Category.objects.get(category_name=cat_val)
            except Category.DoesNotExist:
                return Response({'error': f'Catégorie "{cat_val}" introuvable.'}, status=400)
        except Category.DoesNotExist:
            return Response({'error': f'Catégorie ID {cat_val} introuvable.'}, status=400)

        # ── Résoudre la ville (city ou city_id) ──
        city_val = data.get('city_id') or data.get('city')
        if not city_val:
            return Response({'error': 'city est requis.'}, status=400)
        try:
            city = City.objects.get(pk=int(city_val))
        except (City.DoesNotExist, ValueError, TypeError):
            return Response({'error': f'Ville ID {city_val} introuvable.'}, status=400)

        # ── Coordonnées GPS → Point géographique ──
        lat = data.get('lat')
        lng = data.get('lng')
        if not lat or not lng:
            return Response({'error': 'lat et lng sont requis.'}, status=400)
        try:
            point = Point(float(lng), float(lat), srid=4326)
        except (ValueError, TypeError):
            return Response({'error': 'lat/lng invalides.'}, status=400)

        # ── Champs texte ──
        property_name = data.get('property_name', '').strip()
        if not property_name:
            return Response({'error': 'property_name est requis.'}, status=400)

        price = data.get('price_per_night')
        if not price:
            return Response({'error': 'price_per_night est requis.'}, status=400)

        max_guests = data.get('max_guests', 2)

        # ── Création ──
        prop = Property.objects.create(
            category=category,
            city=city,
            owner=request.user,
            property_name=property_name,
            description=data.get('description', ''),
            price_per_night=price,
            max_guests=max_guests,
            point_geom=point,
            image=request.FILES.get('image'),
            active=True,
        )

        serializer = self.get_serializer(prop, context={'request': request})
        return Response(serializer.data, status=201)


class PropertyDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.filter(active=True)
    serializer_class = PropertySerializer
    name = 'properties-detail'


# ── Cities ──
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


# ── Nearby par property ID ──
@api_view(['GET'])
@permission_classes([AllowAny])
def property_nearby(request, pk):
    prop = get_object_or_404(Property, pk=pk, active=True)
    nearby = (
        Property.objects
        .filter(active=True)
        .exclude(pk=pk)
        .annotate(distance=Distance('point_geom', prop.point_geom))
        .filter(distance__lte=D(km=20))
        .order_by('distance')[:8]
    )
    data = [
        {
            'pk': p.pk,
            'property_name': p.property_name,
            'distance': round(p.distance.m),
            'price_per_night': str(p.price_per_night),
            'city': p.city.city_name if p.city else '',
        }
        for p in nearby
    ]
    return Response(data)


# ── Nearby par coordonnées GPS ──
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_all(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')

    if not lat or not lng:
        return Response({'error': 'Paramètres lat et lng requis.'}, status=400)

    try:
        point = Point(float(lng), float(lat), srid=4326)
    except (ValueError, TypeError):
        return Response({'error': 'lat/lng invalides.'}, status=400)

    city_filter = request.query_params.get('city_filter') == 'true'

    if city_filter:
        nearest_city = (
            City.objects
            .annotate(distance=Distance('point_geom', point))
            .order_by('distance')
            .first()
        )
        if nearest_city:
            qs = (
                Property.objects
                .filter(active=True, city=nearest_city)
                .annotate(distance=Distance('point_geom', point))
                .order_by('distance')[:8]
            )
        else:
            qs = Property.objects.none()
    else:
        qs = (
            Property.objects
            .filter(active=True)
            .annotate(distance=Distance('point_geom', point))
            .filter(distance__lte=D(km=20))
            .order_by('distance')[:8]
        )

    data = [
        {
            'pk': p.pk,
            'property_name': p.property_name,
            'distance': round(p.distance.m),
            'price_per_night': str(p.price_per_night),
            'city': p.city.city_name if p.city else '',
        }
        for p in qs
    ]
    return Response(data)


# ── Bookings ──
@api_view(['POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def booking_create(request):
    """
    POST /bookings/
    Body: { property_id, check_in (YYYY-MM-DD), check_out (YYYY-MM-DD) }
    Returns the created booking or validation errors.
    """
    property_id = request.data.get('property_id')
    check_in    = request.data.get('check_in')
    check_out   = request.data.get('check_out')

    if not property_id or not check_in or not check_out:
        return Response(
            {'error': 'property_id, check_in et check_out sont requis.'},
            status=400
        )

    prop = get_object_or_404(Property, pk=property_id, active=True)

    serializer = BookingSerializer(data={
        'property': prop.pk,
        'check_in': check_in,
        'check_out': check_out,
    }, context={'request': request})

    if serializer.is_valid():
        booking = serializer.save(user=request.user, property=prop)
        return Response(BookingSerializer(booking).data, status=201)

    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def booking_list(request):
    """
    GET /bookings/ → liste des réservations de l'utilisateur connecté.
    """
    bookings = Booking.objects.filter(user=request.user).select_related('property').order_by('-created_at')
    data = [
        {
            'id':            b.id,
            'property_id':   b.property.pk,
            'property_name': b.property.property_name,
            'check_in':      str(b.check_in),
            'check_out':     str(b.check_out),
            'total_price':   str(b.total_price),
            'status':        b.status,
            'created_at':    str(b.created_at),
        }
        for b in bookings
    ]
    return Response(data)


# ── Auth ──
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    data = request.data
    for field in ['username', 'email', 'password']:
        if not data.get(field):
            return Response({'error': f'Le champ "{field}" est obligatoire.'}, status=400)
    try:
        raw_phone = data.get('phone', '')
        phone_value = raw_phone.strip() if raw_phone else None
        phone_value = phone_value or None

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
        error_msg = str(e)
        if 'username' in error_msg and 'already exists' in error_msg:
            return Response({'error': "Ce nom d'utilisateur est déjà utilisé."}, status=400)
        if 'phone_number' in error_msg and 'already exists' in error_msg:
            return Response({'error': 'Ce numéro de téléphone est déjà utilisé.'}, status=400)
        return Response({'error': error_msg}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
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