from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from kbdis.models import AlertEvent, KBDIReading
from peatlandcovers.models import PeatlandSite, VegetationPrediction


def staff_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_staff,
        login_url="management.login",
    )(view_func)


@staff_required
def management_dashboard(request):
    active_sites = PeatlandSite.objects.filter(is_active=True)
    context = {
        "title": "Dashboard",
        "navbar": "dashboard",
        "site_count": active_sites.count(),
        "active_alert_count": AlertEvent.objects.filter(status=AlertEvent.Status.ACTIVE).count(),
        "latest_readings": KBDIReading.objects.select_related("site")[:8],
        "latest_predictions": VegetationPrediction.objects.select_related("site")[:6],
        "active_alerts": AlertEvent.objects.select_related("site", "reading").filter(
            status=AlertEvent.Status.ACTIVE
        )[:6],
        "now": timezone.localtime(),
    }
    return render(request, "management/dashboard.html", context)


def service_worker(request):
    response = render(request, "service-worker.js", content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response
