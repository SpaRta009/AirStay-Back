from .models import Property, Category, City, User, Booking, PropertyImage
from .serializers import CategorySerializer, CitySerializer, PropertySerializer, BookingSerializer, PropertyImageSerializer
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
    serializer_class = PropertySerializer
    name = 'properties-list'
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Property.objects.filter(active=True)

        city = self.request.query_params.get('city', '').strip()
        if city:
            qs = qs.filter(city__city_name__icontains=city)

        guests = self.request.query_params.get('guests', '')
        if guests:
            try:
                qs = qs.filter(max_guests__gte=int(guests))
            except ValueError:
                pass

        property_type = self.request.query_params.get('property_type', '').strip()
        if property_type and property_type != 'All':
            qs = qs.filter(category__category_name__icontains=property_type)

        check_in  = self.request.query_params.get('check_in', '')
        check_out = self.request.query_params.get('check_out', '')
        if check_in and check_out:
            from django.db.models import Q
            booked_ids = Booking.objects.filter(
                status__in=['confirmed', 'paid'],
                check_in__lt=check_out,
                check_out__gt=check_in,
            ).values_list('property_id', flat=True)
            qs = qs.exclude(pk__in=booked_ids)

        return qs

    def create(self, request, *args, **kwargs):
        data = request.data

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

        lat = data.get('lat')
        lng = data.get('lng')
        if not lat or not lng:
            return Response({'error': 'lat et lng sont requis.'}, status=400)
        try:
            point = Point(float(lng), float(lat), srid=4326)
        except (ValueError, TypeError):
            return Response({'error': 'lat/lng invalides.'}, status=400)

        city_val = data.get('city_id') or data.get('city')
        city_name_val = data.get('city_name', '').strip()

        if city_val:
            # Use existing DB city by ID
            try:
                city = City.objects.get(pk=int(city_val))
            except (City.DoesNotExist, ValueError, TypeError):
                return Response({'error': f'Ville ID {city_val} introuvable.'}, status=400)
        elif city_name_val:
            # Auto-create (or get) the city from the name + coordinates
            # get_or_create doesn't support __ lookups, so we do it manually
            city = City.objects.filter(city_name__iexact=city_name_val).first()
            if not city:
                city = City.objects.create(
                    city_name=city_name_val,
                    point_geom=point,
                )
        else:
            return Response({'error': 'city ou city_name est requis.'}, status=400)

        property_name = data.get('property_name', '').strip()
        if not property_name:
            return Response({'error': 'property_name est requis.'}, status=400)

        price = data.get('price_per_night')
        if not price:
            return Response({'error': 'price_per_night est requis.'}, status=400)

        max_guests = data.get('max_guests', 2)

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
    permission_classes = [IsAuthenticatedOrReadOnly]

    def update(self, request, *args, **kwargs):
        prop = self.get_object()
        if request.user != prop.owner:
            return Response(
                {'error': 'You do not have permission to edit this property.'},
                status=403
            )
        return super().update(request, *args, **kwargs)


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


# ── Property images upload ──
@api_view(['POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def property_images_upload(request, pk):
    prop = get_object_or_404(Property, pk=pk, active=True)

    if request.user != prop.owner:
        return Response(
            {'error': 'You do not have permission to upload images for this property.'},
            status=403
        )

    if not request.FILES:
        return Response({'error': 'No images provided.'}, status=400)

    images = request.FILES.getlist('image')
    created_images = []

    for image_file in images:
        if not image_file.content_type.startswith('image/'):
            continue
        img = PropertyImage.objects.create(property=prop, image=image_file)
        created_images.append(PropertyImageSerializer(img).data)

    return Response({'images': created_images}, status=201)


# ── Delete a single PropertyImage ──
@api_view(['DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def property_image_delete(request, pk, img_pk):
    prop = get_object_or_404(Property, pk=pk, active=True)

    if request.user != prop.owner:
        return Response(
            {'error': 'You do not have permission to delete images for this property.'},
            status=403
        )

    img = get_object_or_404(PropertyImage, pk=img_pk, property=prop)
    img.image.delete(save=False)  # remove file from storage
    img.delete()
    return Response(status=204)


# ── Set cover image (promote a PropertyImage → Property.image) ──
@api_view(['PATCH'])
@permission_classes([IsAuthenticatedOrReadOnly])
def property_set_cover(request, pk, img_pk):
    prop = get_object_or_404(Property, pk=pk, active=True)

    if request.user != prop.owner:
        return Response(
            {'error': 'You do not have permission to edit this property.'},
            status=403
        )

    img = get_object_or_404(PropertyImage, pk=img_pk, property=prop)

    # Swap: old cover becomes a PropertyImage, new cover becomes Property.image
    old_cover = prop.image
    new_cover = img.image

    # Save the new file to Property.image field
    prop.image = new_cover
    prop.save(update_fields=['image'])

    # Replace the PropertyImage file with the old cover (if there was one)
    if old_cover:
        img.image = old_cover
        img.save(update_fields=['image'])
    else:
        img.delete()

    serializer = PropertyImageSerializer(img if old_cover else None)
    return Response({'message': 'Cover updated.'}, status=200)


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
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def booking_create(request):
    if request.method == 'GET':
        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'Authentication credentials were not provided.'}, status=401)

        bookings = Booking.objects.filter(user=request.user).select_related('property').prefetch_related('property__images').order_by('-created_at')
        data = [
            {
                'id':            b.id,
                'property_id':   b.property.pk,
                'property_name': b.property.property_name,
                'property_image': (
                    b.property.image.url if b.property.image else None
                ),
                'property_images': [
                    img.image.url for img in b.property.images.all() if img.image
                ],
                'check_in':      str(b.check_in),
                'check_out':     str(b.check_out),
                'total_price':   str(b.total_price),
                'status':        b.status,
                'created_at':    str(b.created_at),
            }
            for b in bookings
        ]
        return Response(data)

    # POST — create a booking
    property_id = request.data.get('property_id')
    check_in    = request.data.get('check_in')
    check_out   = request.data.get('check_out')

    if not property_id or not check_in or not check_out:
        return Response(
            {'error': 'property_id, check_in et check_out sont requis.'},
            status=400
        )

    prop = get_object_or_404(Property, pk=property_id, active=True)

    # ✅ Block host from booking their own property
    if request.user == prop.owner:
        return Response(
            {'error': 'You cannot book your own property.'},
            status=400
        )

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
    bookings = Booking.objects.filter(user=request.user).select_related('property').prefetch_related('property__images').order_by('-created_at')
    data = [
        {
            'id':            b.id,
            'property_id':   b.property.pk,
            'property_name': b.property.property_name,
            'property_image': (
                b.property.image.url if b.property.image else None
            ),
            'property_images': [
                img.image.url for img in b.property.images.all() if img.image
            ],
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