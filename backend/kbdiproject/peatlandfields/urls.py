from django.urls import path

from . import views

urlpatterns = [
    path("", views.peatland_field_list, name="legacy.peatlandfields"),
]
