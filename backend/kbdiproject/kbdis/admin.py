from django.contrib import admin

from .models import AlertEvent, KBDIReading


@admin.register(KBDIReading)
class KBDIReadingAdmin(admin.ModelAdmin):
    list_display = ("site", "observed_at", "kbdi", "level", "rainfall_today_mm", "max_temperature_c")
    list_filter = ("level", "formula_profile", "site")
    search_fields = ("site__name", "site__code")
    readonly_fields = (
        "previous_kbdi",
        "rain_event_accumulation_mm",
        "effective_rainfall_mm",
        "drought_factor",
        "kbdi",
        "level",
        "formula_profile",
        "created_at",
    )


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ("site", "severity", "status", "triggered_at", "cleared_at")
    list_filter = ("severity", "status", "site")
    search_fields = ("site__name", "message")
    readonly_fields = ("triggered_at", "updated_at")
