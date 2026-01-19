from django.urls import path
from . import views
from django.conf.urls import include
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path("categories/", views.CategoryList.as_view(), name=views.CategoryList.name),
    path("categories/<int:pk>/", views.CategoryDetail.as_view(), name=views.CategoryDetail.name),
    path("properties/", views.PropertyList.as_view(), name=views.PropertyList.name),
    path("properties/<int:pk>/", views.PropertyDetail.as_view(), name=views.PropertyDetail.name),
    path("cities/", views.CityList.as_view(), name=views.CityList.name),
    path("api-auth/", include("rest_framework.urls")),
]

urlpatterns = format_suffix_patterns(urlpatterns)
