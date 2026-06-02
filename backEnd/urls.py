from django.urls import path
from . import views
from django.conf.urls import include
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path("categories/",              views.CategoryList.as_view(),   name=views.CategoryList.name),
    path("categories/<int:pk>/",     views.CategoryDetail.as_view(), name=views.CategoryDetail.name),
    path("properties/",              views.PropertyList.as_view(),   name=views.PropertyList.name),
    path("properties/<int:pk>/",     views.PropertyDetail.as_view(), name=views.PropertyDetail.name),

    # ✅ NOUVEAU : nearby depuis une property
    path("properties/<int:pk>/nearby/", views.property_nearby,      name="property-nearby"),

    path("cities/",                  views.CityList.as_view(),       name=views.CityList.name),

    path("properties/<int:pk>/images/", views.property_images_upload, name="property-images-upload"),

    # ✅ NOUVEAU : nearby depuis des coordonnées GPS
    path("nearby-all/",              views.nearby_all,               name="nearby-all"),

    path("auth/register/",           views.register,                 name="register"),
    path("auth/login/",              views.login_view,               name="login"),
    path("bookings/",                views.booking_create,           name="booking-create"),
    path("bookings/list/",           views.booking_list,             name="booking-list"),
    path("api-auth/",                include("rest_framework.urls")),
]

urlpatterns = format_suffix_patterns(urlpatterns)