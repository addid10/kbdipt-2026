from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import OuterRef, Subquery
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from kbdis.models import AlertEvent, KBDIReading
from peatlandcovers.models import PeatlandSite, VegetationPrediction

from .forms import UserRegistrationForm


LEVEL_RANK = {
    KBDIReading.Level.LOW: 0,
    KBDIReading.Level.MODERATE: 1,
    KBDIReading.Level.HIGH: 2,
    KBDIReading.Level.EXTREME: 3,
}


def _safe_next_url(request, fallback):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


def _public_sites():
    """Return active sites with their latest public-facing monitoring state."""

    latest_readings = KBDIReading.objects.filter(site_id=OuterRef("pk")).order_by(
        "-observed_at", "-id"
    )
    latest_predictions = VegetationPrediction.objects.filter(
        site_id=OuterRef("pk")
    ).order_by("-predicted_at", "-id")

    sites = list(
        PeatlandSite.objects.filter(is_active=True).annotate(
            current_reading_id=Subquery(latest_readings.values("id")[:1]),
            previous_reading_id=Subquery(latest_readings.values("id")[1:2]),
            current_prediction_id=Subquery(latest_predictions.values("id")[:1]),
        )
    )

    reading_ids = {
        reading_id
        for site in sites
        for reading_id in (site.current_reading_id, site.previous_reading_id)
        if reading_id is not None
    }
    prediction_ids = {
        site.current_prediction_id
        for site in sites
        if site.current_prediction_id is not None
    }

    readings_by_id = KBDIReading.objects.in_bulk(reading_ids)
    predictions_by_id = VegetationPrediction.objects.in_bulk(prediction_ids)

    for site in sites:
        site.current_reading = readings_by_id.get(site.current_reading_id)
        site.previous_reading = readings_by_id.get(site.previous_reading_id)
        site.current_prediction = predictions_by_id.get(site.current_prediction_id)
        site.kbdi_delta = (
            site.current_reading.kbdi - site.previous_reading.kbdi
            if site.current_reading and site.previous_reading
            else None
        )
        site.level_rank = (
            LEVEL_RANK.get(site.current_reading.level, -1)
            if site.current_reading
            else -1
        )

    sites.sort(
        key=lambda item: (
            item.level_rank,
            item.current_reading.kbdi if item.current_reading else -1,
        ),
        reverse=True,
    )
    return sites


def user_login(request):
    if request.user.is_authenticated:
        return redirect("public.home")

    form = AuthenticationForm(request, data=request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "auth-input")
    form.fields["username"].widget.attrs.update(
        {"placeholder": "Username", "autocomplete": "username"}
    )
    form.fields["password"].widget.attrs.update(
        {"placeholder": "Password", "autocomplete": "current-password"}
    )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if user.is_staff:
            form.add_error(None, "Akun ini tidak digunakan pada portal pengguna.")
        else:
            login(request, user)
            return redirect(_safe_next_url(request, "public.home"))

    return render(
        request,
        "public/login.html",
        {
            "title": "Masuk - KBDIpt",
            "form": form,
            "next": request.POST.get("next") or request.GET.get("next", ""),
        },
    )


def user_register(request):
    if request.user.is_authenticated:
        return redirect("public.home")

    form = UserRegistrationForm(request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "auth-input")
    form.fields["password1"].widget.attrs.update(
        {"placeholder": "Password", "autocomplete": "new-password"}
    )
    form.fields["password2"].widget.attrs.update(
        {"placeholder": "Ulangi password", "autocomplete": "new-password"}
    )

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Akun berhasil dibuat. Selamat datang di KBDIpt.")
        return redirect(_safe_next_url(request, "public.home"))

    return render(
        request,
        "public/register.html",
        {
            "title": "Daftar - KBDIpt",
            "form": form,
            "next": request.POST.get("next") or request.GET.get("next", ""),
        },
    )


def user_logout(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    return redirect("user.login")


@login_required
def home(request):
    sites = _public_sites()
    selected_site = sites[0] if sites else None
    context = {
        "title": "KBDIpt - Sistem Peringatan Dini",
        "nav": "home",
        "sites": sites,
        "selected_site": selected_site,
        "active_alerts": AlertEvent.objects.select_related("site", "reading").filter(
            status=AlertEvent.Status.ACTIVE
        ),
    }
    return render(request, "public/home.html", context)


@login_required
def site_detail(request, code):
    site = get_object_or_404(PeatlandSite, code=code, is_active=True)
    readings = list(site.kbdi_readings.order_by("-observed_at", "-id")[:30])
    prediction = site.vegetation_predictions.order_by("-predicted_at", "-id").first()
    context = {
        "title": f"{site.name} - KBDIpt",
        "nav": "home",
        "site": site,
        "reading": readings[0] if readings else None,
        "previous_reading": readings[1] if len(readings) > 1 else None,
        "kbdi_delta": (
            readings[0].kbdi - readings[1].kbdi if len(readings) > 1 else None
        ),
        "prediction": prediction,
        "readings": readings,
        "active_alert": site.alert_events.filter(
            status=AlertEvent.Status.ACTIVE
        ).first(),
    }
    return render(request, "public/site_detail.html", context)


@login_required
def alerts(request):
    context = {
        "title": "Peringatan - KBDIpt",
        "nav": "alerts",
        "active_alerts": AlertEvent.objects.select_related("site", "reading").filter(
            status=AlertEvent.Status.ACTIVE
        ),
        "alert_history": AlertEvent.objects.select_related("site", "reading").filter(
            status=AlertEvent.Status.CLEARED
        )[:50],
    }
    return render(request, "public/alerts.html", context)


@login_required
def history(request):
    site_id = request.GET.get("site")
    readings = KBDIReading.objects.select_related("site")
    if site_id:
        readings = readings.filter(site_id=site_id)
    context = {
        "title": "Riwayat - KBDIpt",
        "nav": "history",
        "sites": PeatlandSite.objects.filter(is_active=True).order_by("name"),
        "selected_site_id": str(site_id or ""),
        "readings": readings[:100],
    }
    return render(request, "public/history.html", context)


@login_required
def info(request):
    context = {
        "title": "Informasi - KBDIpt",
        "nav": "profile",
    }
    return render(request, "public/info.html", context)


@login_required
def profile(request):
    context = {
        "title": "Profil - KBDIpt",
        "nav": "profile",
        "active_alert_count": AlertEvent.objects.filter(
            status=AlertEvent.Status.ACTIVE
        ).count(),
    }
    return render(request, "public/profile.html", context)


def management_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("management.dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_staff:
            messages.error(request, "Akun ini tidak memiliki akses operator/admin.")
        else:
            login(request, user)
            return redirect(request.GET.get("next") or "management.dashboard")

    return render(
        request,
        "management/login.html",
        {"title": "Login Operator KBDIpt", "form": form},
    )


def management_logout(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    return redirect("management.login")
