from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="kbdis.index"),
    path("alerts/", views.alerts, name="kbdis.alerts"),
]
