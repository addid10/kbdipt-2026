from django.contrib import messages
from django.shortcuts import redirect, render

from kbdiproject.views import staff_required

from .forms import KBDIReadingForm
from .models import AlertEvent, KBDIReading
from .services import create_kbdi_reading


@staff_required
def index(request):
    form = KBDIReadingForm()
    if request.method == "POST":
        form = KBDIReadingForm(request.POST)
        if form.is_valid():
            create_kbdi_reading(
                site=form.cleaned_data["site"],
                observed_at=form.cleaned_data["observed_at"],
                rainfall_today_mm=form.cleaned_data["rainfall_today_mm"],
                rainfall_yesterday_mm=form.cleaned_data["rainfall_yesterday_mm"],
                max_temperature_c=form.cleaned_data["max_temperature_c"],
                water_table_depth_mm=form.cleaned_data.get("water_table_depth_mm"),
                created_by=request.user,
            )
            messages.success(request, "Perhitungan KBDIpt berhasil disimpan.")
            return redirect("kbdis.index")

    context = {
        "title": "KBDIpt",
        "navbar": "kbdi",
        "form": form,
        "readings": KBDIReading.objects.select_related("site")[:30],
        "active_alerts": AlertEvent.objects.select_related("site", "reading").filter(
            status=AlertEvent.Status.ACTIVE
        ),
    }
    return render(request, "management/kbdi.html", context)


@staff_required
def alerts(request):
    context = {
        "title": "Peringatan EWS",
        "navbar": "alerts",
        "active_alerts": AlertEvent.objects.select_related("site", "reading").filter(
            status=AlertEvent.Status.ACTIVE
        ),
        "alert_history": AlertEvent.objects.select_related("site", "reading")[:100],
    }
    return render(request, "management/alerts.html", context)
