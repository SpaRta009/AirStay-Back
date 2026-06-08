from django.urls import path
from . import views
from django.conf.urls import include
from rest_framework.urlpatterns import format_suffix_patterns

# ✅ Routes principales (avec format suffix pour la compatibilité DRF)
api_urlpatterns = [
    path("categories/",              views.CategoryList.as_view(),   name=views.CategoryList.name),
    path("categories/<int:pk>/",     views.CategoryDetail.as_view(), name=views.CategoryDetail.name),
    path("properties/",              views.PropertyList.as_view(),   name=views.PropertyList.name),
    path("properties/<int:pk>/",     views.PropertyDetail.as_view(), name=views.PropertyDetail.name),

    path("properties/<int:pk>/nearby/", views.property_nearby,      name="property-nearby"),

    path("cities/",                  views.CityList.as_view(),       name=views.CityList.name),

    path("properties/<int:pk>/images/", views.property_images_upload, name="property-images-upload"),
    path("properties/<int:pk>/images/<int:img_pk>/delete/", views.property_image_delete, name="property-image-delete"),
    path("properties/<int:pk>/images/<int:img_pk>/set-cover/", views.property_set_cover, name="property-set-cover"),
    # Add to api_urlpatterns (inside format_suffix_patterns):
    path("properties/<int:pk>/bookings/",    views.property_bookings,         name="property-bookings"),
    path("bookings/<int:pk>/status/",        views.booking_update_status,     name="booking-update-status"),

    path("nearby-all/",              views.nearby_all,               name="nearby-all"),

    path("auth/register/",           views.register,                 name="register"),
    path("auth/login/",              views.login_view,               name="login"),
    path("bookings/",                views.booking_create,           name="booking-create"),
    path("bookings/list/",           views.booking_list,             name="booking-list"),

    path("api-auth/",                include("rest_framework.urls")),

    # Add to wishlist_urlpatterns (outside format_suffix_patterns):
    path("notifications/",                   views.notification_list,         name="notification-list"),
    path("notifications/read-all/",          views.notification_mark_all_read, name="notification-read-all"),
    path("notifications/<int:pk>/read/",     views.notification_mark_read,    name="notification-mark-read"),
    path("notifications/<int:pk>/",          views.notification_delete,       name="notification-delete"),
]

# ✅ Routes wishlist séparées — exclues de format_suffix_patterns
# pour éviter que DELETE /wishlist/5/ soit interprété comme un format suffix
wishlist_urlpatterns = [
    path("wishlist/",                    views.wishlist_list,    name="wishlist-list"),
    path("wishlist/<int:property_id>/",  views.wishlist_toggle,  name="wishlist-toggle"),
]

urlpatterns = format_suffix_patterns(api_urlpatterns) + wishlist_urlpatterns