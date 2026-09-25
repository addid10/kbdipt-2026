from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import views


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("users.urls")),
    path("management/", views.management_dashboard, name="management.dashboard"),
    path("management/vegetation/", include("peatlandcovers.urls")),
    path("management/kbdi/", include("kbdis.urls")),
    path("api/v1/", include("kbdiproject.api_urls")),
    path("service-worker.js", views.service_worker, name="service-worker"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
