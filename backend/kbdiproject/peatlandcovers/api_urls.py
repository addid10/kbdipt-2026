from django.urls import path

from .api_views import (
    PeatlandSiteListAPIView,
    VegetationPredictAPIView,
    VegetationPredictionListAPIView,
)

urlpatterns = [
    path("sites/", PeatlandSiteListAPIView.as_view(), name="api.sites"),
    path("predictions/", VegetationPredictionListAPIView.as_view(), name="api.vegetation.predictions"),
    path("predict/", VegetationPredictAPIView.as_view(), name="api.vegetation.predict"),
]
