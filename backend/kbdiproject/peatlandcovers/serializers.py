from rest_framework import serializers

from .models import PeatlandSite, VegetationPrediction


class PeatlandSiteSerializer(serializers.ModelSerializer):
    latest_vegetation = serializers.SerializerMethodField()

    class Meta:
        model = PeatlandSite
        fields = [
            "id",
            "name",
            "code",
            "location",
            "latitude",
            "longitude",
            "area_hectares",
            "land_type",
            "protection_status",
            "is_active",
            "latest_vegetation",
            "updated_at",
        ]

    def get_latest_vegetation(self, obj):
        prediction = obj.vegetation_predictions.order_by("-predicted_at").first()
        if not prediction:
            return None
        return {
            "class": prediction.vegetation_class,
            "label": prediction.get_vegetation_class_display(),
            "confidence": prediction.confidence,
            "model_version": prediction.model_version,
            "predicted_at": prediction.predicted_at,
        }


class VegetationPredictionSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)
    vegetation_label = serializers.CharField(source="get_vegetation_class_display", read_only=True)

    class Meta:
        model = VegetationPrediction
        fields = [
            "id",
            "site",
            "site_name",
            "image",
            "vegetation_class",
            "vegetation_label",
            "confidence",
            "model_version",
            "source",
            "predicted_at",
        ]
        read_only_fields = [
            "vegetation_class",
            "confidence",
            "model_version",
            "source",
            "predicted_at",
        ]
