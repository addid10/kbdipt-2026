"""KBDIpt calculation and early-warning alert orchestration.

The default constants and class thresholds follow Novitasari et al. (2019),
"Drought Index for Peatland Wildfire Management in Central Kalimantan,
Indonesia During El Niño Phenomenon".

Important implementation detail:
- wc is the reference available-water capacity used by the published KBDIpt
  formulation (400 mm). A daily measured water-table depth is stored as an
  observation, but it is not substituted for wc.
- Vegetation classification is kept as a separate monitoring feature because
  the cited KBDIpt equation does not use vegetation class as a direct input.
"""

from dataclasses import dataclass
from datetime import timedelta
import math

from django.db import transaction
from django.utils import timezone

from .models import AlertEvent, KBDIReading


@dataclass(frozen=True)
class KBDIProfile:
    name: str
    average_annual_rainfall_mm: float
    coefficient_a: float
    coefficient_b: float
    coefficient_c: float
    field_capacity_mm: float


NOVITASARI_2019 = KBDIProfile(
    name=KBDIReading.FormulaProfile.NOVITASARI_2019,
    average_annual_rainfall_mm=1650.0,
    coefficient_a=0.3614,
    coefficient_b=0.0905,
    coefficient_c=3.10,
    field_capacity_mm=400.0,
)

RAIN_THRESHOLD_MM = 5.1


def classify_kbdi(kbdi: float) -> str:
    if kbdi <= 200.0:
        return KBDIReading.Level.LOW
    if kbdi <= 300.0:
        return KBDIReading.Level.MODERATE
    if kbdi <= 350.0:
        return KBDIReading.Level.HIGH
    return KBDIReading.Level.EXTREME


def calculate_effective_rainfall(
    rainfall_today_mm: float,
    previous_event_accumulation_mm: float,
) -> tuple[float, float]:
    """Return today's effective rainfall and the updated rain-event accumulation.

    KBDI ignores the first 5.1 mm of a continuous rain event. This event-based
    implementation also reproduces the two-day example used in the Liang
    Anggang KBDI study (4.7 mm followed by 4.8 mm gives 4.4 mm effective rain
    on the second day).
    """

    rainfall_today_mm = max(float(rainfall_today_mm), 0.0)
    previous_event_accumulation_mm = max(float(previous_event_accumulation_mm), 0.0)

    if rainfall_today_mm <= 0:
        return 0.0, 0.0

    new_accumulation = previous_event_accumulation_mm + rainfall_today_mm
    previous_excess = max(previous_event_accumulation_mm - RAIN_THRESHOLD_MM, 0.0)
    new_excess = max(new_accumulation - RAIN_THRESHOLD_MM, 0.0)
    effective_today = max(new_excess - previous_excess, 0.0)
    return effective_today, new_accumulation


def calculate_drought_factor(
    adjusted_previous_kbdi: float,
    max_temperature_c: float,
    profile: KBDIProfile = NOVITASARI_2019,
) -> float:
    adjusted_previous_kbdi = max(min(float(adjusted_previous_kbdi), profile.field_capacity_mm), 0.0)
    remaining_capacity = max(profile.field_capacity_mm - adjusted_previous_kbdi, 0.0)

    numerator = (
        profile.coefficient_a
        * math.exp(profile.coefficient_b * float(max_temperature_c) + 1.5552)
        - profile.coefficient_c
    ) * 1e-3
    denominator = 1 + 10.88 * math.exp(
        -0.001736 * profile.average_annual_rainfall_mm
    )

    return max(remaining_capacity * numerator / denominator, 0.0)


def calculate_kbdi(
    previous_kbdi: float,
    rainfall_today_mm: float,
    max_temperature_c: float,
    previous_event_accumulation_mm: float = 0.0,
    profile: KBDIProfile = NOVITASARI_2019,
) -> dict:
    effective_rainfall, event_accumulation = calculate_effective_rainfall(
        rainfall_today_mm,
        previous_event_accumulation_mm,
    )
    adjusted_previous = max(float(previous_kbdi) - effective_rainfall, 0.0)
    drought_factor = calculate_drought_factor(adjusted_previous, max_temperature_c, profile)
    kbdi = min(adjusted_previous + drought_factor, profile.field_capacity_mm)

    return {
        "previous_kbdi": float(previous_kbdi),
        "effective_rainfall_mm": effective_rainfall,
        "rain_event_accumulation_mm": event_accumulation,
        "adjusted_previous_kbdi": adjusted_previous,
        "drought_factor": drought_factor,
        "kbdi": kbdi,
        "level": classify_kbdi(kbdi),
        "formula_profile": profile.name,
    }


def _resolve_previous_event_accumulation(site, observed_at, rainfall_yesterday_mm):
    previous = (
        KBDIReading.objects.filter(site=site, observed_at__lt=observed_at)
        .order_by("-observed_at", "-id")
        .first()
    )
    if previous:
        time_gap = observed_at - previous.observed_at
        if time_gap <= timedelta(hours=36) and previous.rainfall_today_mm > 0:
            return previous, previous.rain_event_accumulation_mm

    # If no immediately preceding database reading is available, seed the
    # event with the user-provided rainfall from yesterday.
    return previous, max(float(rainfall_yesterday_mm or 0.0), 0.0)


def _alert_message(level: str, site_name: str) -> str:
    if level == KBDIReading.Level.EXTREME:
        return f"Kondisi KBDIpt ekstrem terdeteksi di {site_name}. Alarm darurat aktif."
    return f"Kondisi KBDIpt tinggi terdeteksi di {site_name}. Alarm peringatan aktif."


@transaction.atomic
def sync_alert_for_reading(reading: KBDIReading):
    active_alert = (
        AlertEvent.objects.select_for_update()
        .filter(site=reading.site, status=AlertEvent.Status.ACTIVE)
        .first()
    )

    if not reading.alarm_active:
        if active_alert:
            active_alert.status = AlertEvent.Status.CLEARED
            active_alert.cleared_at = reading.observed_at
            active_alert.reading = reading
            active_alert.save(update_fields=["status", "cleared_at", "reading", "updated_at"])
        return None

    if active_alert and active_alert.severity == reading.level:
        active_alert.reading = reading
        active_alert.message = _alert_message(reading.level, reading.site.name)
        active_alert.save(update_fields=["reading", "message", "updated_at"])
        return active_alert

    if active_alert:
        active_alert.status = AlertEvent.Status.CLEARED
        active_alert.cleared_at = reading.observed_at
        active_alert.save(update_fields=["status", "cleared_at", "updated_at"])

    return AlertEvent.objects.create(
        site=reading.site,
        reading=reading,
        severity=reading.level,
        message=_alert_message(reading.level, reading.site.name),
        triggered_at=reading.observed_at,
    )


@transaction.atomic
def create_kbdi_reading(
    *,
    site,
    observed_at,
    rainfall_today_mm,
    rainfall_yesterday_mm,
    max_temperature_c,
    water_table_depth_mm=None,
    created_by=None,
):
    previous_reading, previous_event_accumulation = _resolve_previous_event_accumulation(
        site,
        observed_at,
        rainfall_yesterday_mm,
    )
    # The first chronological reading starts from KBDIpt = 0.
    # Every later reading automatically uses the latest earlier reading
    # from the same site as KBDI(t-1). Operators and API clients do not
    # provide a previous/initial KBDIpt value.
    previous_kbdi = float(previous_reading.kbdi) if previous_reading is not None else 0.0

    result = calculate_kbdi(
        previous_kbdi=previous_kbdi,
        rainfall_today_mm=rainfall_today_mm,
        max_temperature_c=max_temperature_c,
        previous_event_accumulation_mm=previous_event_accumulation,
    )

    reading = KBDIReading.objects.create(
        site=site,
        observed_at=observed_at,
        rainfall_today_mm=rainfall_today_mm,
        rainfall_yesterday_mm=rainfall_yesterday_mm,
        max_temperature_c=max_temperature_c,
        water_table_depth_mm=water_table_depth_mm,
        previous_kbdi=result["previous_kbdi"],
        rain_event_accumulation_mm=result["rain_event_accumulation_mm"],
        effective_rainfall_mm=result["effective_rainfall_mm"],
        drought_factor=result["drought_factor"],
        kbdi=result["kbdi"],
        level=result["level"],
        formula_profile=result["formula_profile"],
        created_by=created_by,
    )
    sync_alert_for_reading(reading)
    return reading
