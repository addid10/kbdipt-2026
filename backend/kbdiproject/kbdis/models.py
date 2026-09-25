from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from peatlandcovers.models import PeatlandCover, PeatlandSite


class DroughtIndex(models.Model):
    """Legacy prototype model retained for migration compatibility."""

    kbdi = models.FloatField()
    date = models.DateField(auto_now_add=True)
    peatland_cover = models.ForeignKey(PeatlandCover, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kbdi:.2f}"

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Legacy drought index"
        verbose_name_plural = "Legacy drought indices"


class DroughtFactor(models.Model):
    """Legacy prototype model retained for migration compatibility."""

    drought_factor = models.FloatField()
    date = models.DateField(auto_now_add=True)
    peatland_cover = models.ForeignKey(PeatlandCover, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.drought_factor:.2f}"

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Legacy drought factor"
        verbose_name_plural = "Legacy drought factors"


class KBDIReading(models.Model):
    class Level(models.TextChoices):
        LOW = "low", "Low"
        MODERATE = "moderate", "Moderat"
        HIGH = "high", "High"
        EXTREME = "extreme", "Extreme"

    class FormulaProfile(models.TextChoices):
        NOVITASARI_2019 = "novitasari_2019", "Novitasari et al. (2019) - tropical peatland"

    site = models.ForeignKey(PeatlandSite, related_name="kbdi_readings", on_delete=models.CASCADE)
    observed_at = models.DateTimeField()
    rainfall_today_mm = models.FloatField(validators=[MinValueValidator(0.0)])
    rainfall_yesterday_mm = models.FloatField(validators=[MinValueValidator(0.0)], default=0.0)
    max_temperature_c = models.FloatField()
    water_table_depth_mm = models.FloatField(
        null=True,
        blank=True,
        help_text="Observed water table depth below the peat surface. Stored for monitoring; not substituted for wc in the KBDIpt equation.",
    )
    previous_kbdi = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    rain_event_accumulation_mm = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    effective_rainfall_mm = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    drought_factor = models.FloatField(default=0.0)
    kbdi = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(400.0)]
    )
    level = models.CharField(max_length=20, choices=Level.choices)
    formula_profile = models.CharField(
        max_length=40,
        choices=FormulaProfile.choices,
        default=FormulaProfile.NOVITASARI_2019,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="kbdi_readings",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at", "-id"]
        indexes = [
            models.Index(fields=["site", "-observed_at"], name="kbdi_site_time_idx"),
            models.Index(fields=["level", "-observed_at"], name="kbdi_level_time_idx"),
        ]

    def __str__(self):
        return f"{self.site.name} - {self.kbdi:.1f} ({self.get_level_display()})"

    @property
    def alarm_active(self):
        return self.level in {self.Level.HIGH, self.Level.EXTREME}


class AlertEvent(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        CLEARED = "cleared", "Selesai"

    site = models.ForeignKey(PeatlandSite, related_name="alert_events", on_delete=models.CASCADE)
    reading = models.ForeignKey(KBDIReading, related_name="alert_events", on_delete=models.PROTECT)
    severity = models.CharField(
        max_length=20,
        choices=[
            (KBDIReading.Level.HIGH, "High"),
            (KBDIReading.Level.EXTREME, "Extreme"),
        ],
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    message = models.CharField(max_length=255)
    triggered_at = models.DateTimeField()
    cleared_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-triggered_at", "-id"]
        indexes = [
            models.Index(fields=["site", "status"], name="alert_site_status_idx"),
            models.Index(fields=["severity", "-triggered_at"], name="alert_sev_time_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["site"],
                condition=Q(status="active"),
                name="one_active_alert_per_site",
            )
        ]

    def __str__(self):
        return f"{self.site.name} - {self.severity.upper()} - {self.status}"
