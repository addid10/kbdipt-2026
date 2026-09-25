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
    initial_kbdi = forms.FloatField(
        label="KBDIpt Awal",
        required=False,
        min_value=0,
        max_value=400,
        help_text="Hanya diperlukan untuk pengukuran pertama pada lokasi ini.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = PeatlandSite.objects.filter(is_active=True).order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        site = cleaned_data.get("site")
        observed_at = cleaned_data.get("observed_at")
        initial_kbdi = cleaned_data.get("initial_kbdi")

        if not site or not observed_at:
            return cleaned_data

        has_previous_reading = site.kbdi_readings.filter(observed_at__lt=observed_at).exists()
        if not has_previous_reading and initial_kbdi in (None, ""):
            self.add_error(
                "initial_kbdi",
                "KBDIpt awal wajib diisi karena belum ada pengukuran sebelumnya untuk lokasi ini.",
            )

        # Once a previous reading exists, the backend always uses that reading.
        # Any stale value left in the form must not become an override.
        if has_previous_reading:
            cleaned_data["initial_kbdi"] = None

        return cleaned_data
