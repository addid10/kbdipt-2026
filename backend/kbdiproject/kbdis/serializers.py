from django.utils import timezone
from rest_framework import serializers

from peatlandcovers.models import PeatlandSite

from .models import AlertEvent, KBDIReading
from .services import create_kbdi_reading


class KBDIReadingSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    alarm = serializers.BooleanField(source="alarm_active", read_only=True)

    class Meta:
        model = KBDIReading
        fields = [
            "id",
            "site",
            "site_name",
            "observed_at",
            "rainfall_today_mm",
            "rainfall_yesterday_mm",
            "max_temperature_c",
            "water_table_depth_mm",
            "previous_kbdi",
            "effective_rainfall_mm",
            "drought_factor",
            "kbdi",
            "level",
            "level_label",
            "alarm",
            "formula_profile",
            "created_at",
        ]
        read_only_fields = [
            "previous_kbdi",
            "effective_rainfall_mm",
            "drought_factor",
            "kbdi",
            "level",
            "formula_profile",
            "created_at",
        ]


class KBDIReadingCreateSerializer(serializers.Serializer):
    site = serializers.PrimaryKeyRelatedField(queryset=PeatlandSite.objects.filter(is_active=True))
    observed_at = serializers.DateTimeField(required=False)
    rainfall_today_mm = serializers.FloatField(min_value=0)
    rainfall_yesterday_mm = serializers.FloatField(min_value=0, default=0)
    max_temperature_c = serializers.FloatField()
    water_table_depth_mm = serializers.FloatField(required=False, allow_null=True, min_value=0)
    initial_kbdi = serializers.FloatField(required=False, min_value=0, max_value=400)

    def validate(self, attrs):
        site = attrs.get("site")
        observed_at = attrs.get("observed_at") or timezone.now()
        attrs["observed_at"] = observed_at

        has_previous_reading = site.kbdi_readings.filter(observed_at__lt=observed_at).exists()
        if not has_previous_reading and attrs.get("initial_kbdi") is None:
            raise serializers.ValidationError(
                {
                    "initial_kbdi": (
                        "This is the first KBDIpt reading for the site. "
                        "Provide the initial KBDIpt value."
                    )
                }
            )

        # initial_kbdi is only a seed for the first chronological reading.
        # It can never override an existing previous KBDIpt value.
        if has_previous_reading:
            attrs.pop("initial_kbdi", None)
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        return create_kbdi_reading(
            site=validated_data["site"],
            observed_at=validated_data["observed_at"],
            rainfall_today_mm=validated_data["rainfall_today_mm"],
            rainfall_yesterday_mm=validated_data.get("rainfall_yesterday_mm", 0),
            max_temperature_c=validated_data["max_temperature_c"],
            water_table_depth_mm=validated_data.get("water_table_depth_mm"),
            initial_kbdi=validated_data.get("initial_kbdi"),
            created_by=request.user if request and request.user.is_authenticated else None,
        )


class AlertEventSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)
    kbdi = serializers.FloatField(source="reading.kbdi", read_only=True)
    observed_at = serializers.DateTimeField(source="reading.observed_at", read_only=True)

    class Meta:
        model = AlertEvent
        fields = [
            "id",
            "site",
            "site_name",
            "severity",
            "status",
            "message",
            "kbdi",
            "observed_at",
            "triggered_at",
            "cleared_at",
            "updated_at",
        ]
