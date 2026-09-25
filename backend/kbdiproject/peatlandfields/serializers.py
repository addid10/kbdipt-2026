from rest_framework import serializers

from .models import PeatlandField


class PeatlandFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeatlandField
        fields = ["id", "water_level", "max_air_temperature", "date", "peatland_cover", "created_at"]
