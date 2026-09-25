from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class PeatlandCover(models.Model):
    """Legacy model retained so existing prototype databases can still migrate safely."""

    name = models.CharField(max_length=255)
    image = models.CharField(max_length=255)
    result_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Legacy peatland cover"
        verbose_name_plural = "Legacy peatland covers"


class PeatlandSite(models.Model):
    class ProtectionStatus(models.TextChoices):
        PROTECTED = "protected", "Terlindungi"
        MANAGED = "managed", "Dikelola"
        OTHER = "other", "Lainnya"

    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=80, unique=True)
    location = models.CharField(max_length=255, default="Banjarbaru, Kalimantan Selatan")
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    area_hectares = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    land_type = models.CharField(max_length=120, default="Lahan gambut")
    protection_status = models.CharField(
        max_length=20,
        choices=ProtectionStatus.choices,
        default=ProtectionStatus.PROTECTED,
    )
    cover_image = models.ImageField(upload_to="peatland_sites/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def latest_prediction(self):
        prefetched = getattr(self, "_prefetched_objects_cache", {}).get("vegetation_predictions")
        if prefetched is not None:
            return prefetched[0] if prefetched else None
        return self.vegetation_predictions.order_by("-predicted_at").first()


class VegetationPrediction(models.Model):
    class VegetationClass(models.TextChoices):
        DENSE = "dense", "Tinggi"
        MEDIUM = "medium", "Sedang"
        BARE = "bare", "Terbuka/Bare"

    class Source(models.TextChoices):
        MODEL = "model", "Model AI"
        MANUAL = "manual", "Manual"

    site = models.ForeignKey(
        PeatlandSite,
        related_name="vegetation_predictions",
        on_delete=models.CASCADE,
    )
    image = models.ImageField(upload_to="vegetation_predictions/%Y/%m/")
    vegetation_class = models.CharField(max_length=20, choices=VegetationClass.choices)
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0,
    )
    model_version = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MODEL)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vegetation_predictions",
    )
    predicted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-predicted_at"]
        indexes = [models.Index(fields=["site", "-predicted_at"], name="vegpred_site_time_idx")]

    def __str__(self):
        return f"{self.site.name} - {self.get_vegetation_class_display()}"
