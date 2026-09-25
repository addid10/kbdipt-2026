from django.urls import include, path

from kbdis.api_views import ActiveAlertListAPIView, EWSStatusAPIView, KBDIReadingListCreateAPIView

urlpatterns = [
    path("vegetation/", include("peatlandcovers.api_urls")),
    path("kbdi/readings/", KBDIReadingListCreateAPIView.as_view(), name="api.kbdi.readings"),
    path("ews/status/<int:site_id>/", EWSStatusAPIView.as_view(), name="api.ews.status"),
    path("ews/alerts/", ActiveAlertListAPIView.as_view(), name="api.ews.alerts"),
]
