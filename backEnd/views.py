from .models import Property, Category, City, User, Booking, PropertyImage, Wishlist
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
# ── Imports to add at the top of views.py ──
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta


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
            try:
                city = City.objects.get(pk=int(city_val))
            except (City.DoesNotExist, ValueError, TypeError):
                return Response({'error': f'Ville ID {city_val} introuvable.'}, status=400)
        elif city_name_val:
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
        # ✅ FIX: passer request dans le contexte pour avoir l'URL absolue
        created_images.append(PropertyImageSerializer(img, context={'request': request}).data)

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
    img.image.delete(save=False)
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

    old_cover = prop.image
    new_cover = img.image

    prop.image = new_cover
    prop.save(update_fields=['image'])

    if old_cover:
        img.image = old_cover
        img.save(update_fields=['image'])
    else:
        img.delete()

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


# ── Helpers ──
def _build_image_url(request, url):
    """Retourne une URL absolue pour une image (corrige le problème multi-appareil)."""
    if not url:
        return None
    if url.startswith('http'):
        return url
    return request.build_absolute_uri(url)


def _serialize_booking(b, request):
    """Sérialise un booking avec des URLs d'images absolues."""
    return {
        'id':            b.id,
        'property_id':   b.property.pk,
        'property_name': b.property.property_name,
        # ✅ FIX: URL absolue — visible depuis n'importe quel appareil
        'property_image': _build_image_url(
            request,
            b.property.image.url if b.property.image else None
        ),
        # ✅ FIX: URLs absolues pour toutes les images supplémentaires
        'property_images': [
            _build_image_url(request, img.image.url)
            for img in b.property.images.all() if img.image
        ],
        'check_in':      str(b.check_in),
        'check_out':     str(b.check_out),
        'total_price':   str(b.total_price),
        'status':        b.status,
        'created_at':    str(b.created_at),
    }


# ── Bookings ──
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def booking_create(request):
    if request.method == 'GET':
        if not request.user or not request.user.is_authenticated:
            return Response({'error': 'Authentication credentials were not provided.'}, status=401)

        bookings = (
            Booking.objects
            .filter(user=request.user)
            .select_related('property')
            .prefetch_related('property__images')
            .order_by('-created_at')
        )
        data = [_serialize_booking(b, request) for b in bookings]
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
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('property')
        .prefetch_related('property__images')
        .order_by('-created_at')
    )
    data = [_serialize_booking(b, request) for b in bookings]
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


# ── Wishlist ──

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def wishlist_list(request):
    """Retourne la liste des IDs de propriétés sauvegardées par l'utilisateur."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required.'}, status=401)

    ids = list(
        Wishlist.objects
        .filter(user=request.user)
        .values_list('property_id', flat=True)
    )
    return Response({'favorites': ids})


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def wishlist_toggle(request, property_id):
    """
    POST   → ajoute la propriété à la wishlist (idempotent)
    DELETE → retire la propriété de la wishlist
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required.'}, status=401)

    prop = get_object_or_404(Property, pk=property_id, active=True)

    if request.method == 'POST':
        _, created = Wishlist.objects.get_or_create(user=request.user, property=prop)
        return Response({'added': True, 'created': created}, status=201 if created else 200)

    # DELETE
    deleted, _ = Wishlist.objects.filter(user=request.user, property=prop).delete()
    return Response({'removed': deleted > 0}, status=200)

# ── Helper: create a notification ──
def create_notification(user, notif_type, title, message, property_obj=None, booking_obj=None):
    Notification.objects.create(
        user=user,
        type=notif_type,
        title=title,
        message=message,
        property=property_obj,
        booking=booking_obj,
    )
 
 
# ── GET /notifications/  — list all notifications for current user ──
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    try:
        notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
        # ✅ FIX : Ajout indispensable de context={'request': request}
        serializer = NotificationSerializer(notifs, many=True, context={'request': request})
        return Response(serializer.data, status=200)
    except Exception as e:
        # ✅ Si un autre bug subsiste, il s'affichera dans l'onglet Network au lieu d'un crash 500
        return Response({"error_debug": str(e)}, status=500)
 
 
# ── POST /notifications/<id>/read/  — mark one as read ──
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    try:
        notif = Notification.objects.get(pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return Response({'status': 'ok'}, status=200)
    except Notification.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
 
 
# ── POST /notifications/read-all/  — mark all as read ──
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'status': 'ok'}, status=200)
 
 
# ── DELETE /notifications/<id>/  — dismiss a notification ──
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def notification_delete(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).delete()
    # ✅ FIX : Utilisation directe du code 204 brut pour éviter les conflits d'import de 'status'
    return Response(status=204)
 
 
# ── GET /properties/<pk>/bookings/  — list bookings for a property (host only) ──
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def property_bookings(request, pk):
    from .models import Property, Booking
    try:
        property_obj = Property.objects.get(pk=pk)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=404)
 
    if property_obj.owner != request.user:
        return Response({'error': 'Forbidden'}, status=403)
 
    bookings = Booking.objects.filter(property=property_obj).select_related('user').order_by('-created_at')
 
    # Auto-expire pending bookings older than 48 hours
    cutoff = timezone.now() - timedelta(hours=48)
    expired_qs = bookings.filter(status='pending', created_at__lt=cutoff)
    for booking in expired_qs:
        booking.status = 'canceled'
        booking.save(update_fields=['status'])
        # Notify host
        create_notification(
            request.user, 'booking_expired',
            'Booking request expired',
            f'Booking #{booking.id} from {booking.user.username} expired without response.',
            property_obj, booking
        )
        # Notify guest
        create_notification(
            booking.user, 'booking_expired',
            'Booking request expired',
            f'Your request for {property_obj.property_name} expired — no response within 48 hours.',
            property_obj, booking
        )
 
    data = []
    for b in bookings.order_by('-created_at'):
        data.append({
            'id': b.id,
            'user': {'id': b.user.id, 'username': b.user.username},
            'check_in': str(b.check_in),
            'check_out': str(b.check_out),
            'total_price': str(b.total_price),
            'status': b.status,
            'created_at': b.created_at.isoformat(),
        })
    return Response(data)
 
 
# ── PATCH /bookings/<id>/status/  — confirm or cancel a booking (host only) ──
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def booking_update_status(request, pk):
    from .models import Booking
    try:
        booking = Booking.objects.select_related('property', 'user').get(pk=pk)
    except Booking.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
 
    # Only the property owner can change booking status
    if booking.property.owner != request.user:
        return Response({'error': 'Forbidden'}, status=403)
 
    new_status = request.data.get('status')
    allowed = ['confirmed', 'canceled', 'completed']
    if new_status not in allowed:
        return Response({'error': f'Status must be one of {allowed}'}, status=400)
 
    booking.status = new_status
    booking.save(update_fields=['status'])
 
    prop = booking.property
    guest = booking.user
    host  = request.user
 
    if new_status == 'confirmed':
        # Notify guest
        create_notification(
            guest, 'booking_confirmed',
            'Booking confirmed! 🎉',
            f'Your reservation at {prop.property_name} ({booking.check_in} → {booking.check_out}) has been confirmed.',
            prop, booking
        )
        # Notify host
        create_notification(
            host, 'booking_confirmed',
            'You confirmed a booking',
            f'You confirmed the booking from {guest.username} at {prop.property_name}.',
            prop, booking
        )
 
    elif new_status == 'canceled':
        create_notification(
            guest, 'booking_canceled',
            'Booking declined',
            f'Your reservation request at {prop.property_name} was declined by the host.',
            prop, booking
        )
        create_notification(
            host, 'booking_canceled',
            'Booking declined',
            f'You declined the reservation from {guest.username}.',
            prop, booking
        )
 
    elif new_status == 'completed':
        create_notification(
            guest, 'booking_completed',
            'Stay completed',
            f'We hope you enjoyed your stay at {prop.property_name}! Leave a review.',
            prop, booking
        )
        create_notification(
            host, 'booking_completed',
            'Stay completed',
            f'{guest.username} has checked out from {prop.property_name}.',
            prop, booking
        )
 
    return Response({'status': new_status})

