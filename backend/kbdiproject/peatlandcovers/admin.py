from django.contrib import admin

from .models import PeatlandSite, VegetationPrediction


@admin.register(PeatlandSite)
class PeatlandSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "location", "protection_status", "is_active", "updated_at")
    list_filter = ("is_active", "protection_status")
    search_fields = ("name", "code", "location")


@admin.register(VegetationPrediction)
class VegetationPredictionAdmin(admin.ModelAdmin):
    list_display = ("site", "vegetation_class", "confidence", "model_version", "predicted_at")
    list_filter = ("vegetation_class", "source", "model_version")
    search_fields = ("site__name",)
    readonly_fields = ("predicted_at",)
