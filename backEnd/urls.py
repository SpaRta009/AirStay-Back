from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

api_urlpatterns = [
    # ───── Categories ─────
    path("categories/", views.CategoryList.as_view()),
    path("categories/<int:pk>/", views.CategoryDetail.as_view()),

    # ───── Properties ─────
    path("properties/", views.PropertyList.as_view()),
    path("properties/<int:pk>/", views.PropertyDetail.as_view()),
    path("properties/<int:pk>/nearby/", views.property_nearby),

    # images
    path("properties/<int:pk>/images/", views.property_images_upload),
    path("properties/<int:pk>/images/<int:img_pk>/delete/", views.property_image_delete),
    path("properties/<int:pk>/images/<int:img_pk>/set-cover/", views.property_set_cover),

    # bookings
    path("bookings/", views.booking_create),
    path("bookings/list/", views.booking_list),
    path("properties/<int:pk>/bookings/", views.property_bookings),
    path("bookings/<int:pk>/status/", views.booking_update_status),

    # auth
    path("auth/register/", views.register),
    path("auth/login/", views.login_view),

    # cities
    path("cities/", views.CityList.as_view()),

    # nearby
    path("nearby-all/", views.nearby_all),

    # ───── Notifications ─────
    path("notifications/", views.notification_list),
    path("notifications/read-all/", views.notification_mark_all_read),
    path("notifications/<int:pk>/read/", views.notification_mark_read),
    path("notifications/<int:pk>/", views.notification_delete),

    path("api-auth/", include("rest_framework.urls")),
]

wishlist_urlpatterns = [
    path("wishlist/", views.wishlist_list),
    path("wishlist/<int:property_id>/", views.wishlist_toggle),
]

urlpatterns = format_suffix_patterns(api_urlpatterns) + wishlist_urlpatterns