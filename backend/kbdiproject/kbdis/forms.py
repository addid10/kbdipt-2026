from django import forms
from django.utils import timezone

from peatlandcovers.models import PeatlandSite


class KBDIReadingForm(forms.Form):
    site = forms.ModelChoiceField(
        queryset=PeatlandSite.objects.none(),
        label="Lokasi",
    )
    observed_at = forms.DateTimeField(
        label="Waktu Pengamatan",
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"],
    )
    rainfall_today_mm = forms.FloatField(label="Curah Hujan Hari Ini (mm)", min_value=0)
    rainfall_yesterday_mm = forms.FloatField(
        label="Curah Hujan Kemarin (mm)",
        min_value=0,
        initial=0,
    )
    max_temperature_c = forms.FloatField(label="Suhu Maksimum (°C)")
    water_table_depth_mm = forms.FloatField(
        label="Kedalaman Muka Air (mm)",
        required=False,
        min_value=0,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = PeatlandSite.objects.filter(is_active=True).order_by("name")
