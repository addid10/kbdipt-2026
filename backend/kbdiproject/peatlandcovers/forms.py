from decimal import Decimal, ROUND_HALF_UP

from django import forms

from .models import PeatlandSite


COORDINATE_QUANTUM = Decimal("0.0000001")


class PeatlandSiteForm(forms.ModelForm):
    # Accept coordinates pasted from GPS/Google Maps with arbitrary precision.
    # They are normalized to the model's 7 decimal places before saving.
    latitude = forms.DecimalField(
        required=False,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
        widget=forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
    )
    longitude = forms.DecimalField(
        required=False,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
        widget=forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
    )

    class Meta:
        model = PeatlandSite
        fields = [
            "name",
            "code",
            "location",
            "latitude",
            "longitude",
            "area_hectares",
            "land_type",
            "protection_status",
            "cover_image",
            "description",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    @staticmethod
    def _normalize_coordinate(value):
        if value is None:
            return None
        return value.quantize(COORDINATE_QUANTUM, rounding=ROUND_HALF_UP)

    def clean_latitude(self):
        return self._normalize_coordinate(self.cleaned_data.get("latitude"))

    def clean_longitude(self):
        return self._normalize_coordinate(self.cleaned_data.get("longitude"))


class VegetationPredictionForm(forms.Form):
    site = forms.ModelChoiceField(queryset=PeatlandSite.objects.none())
    image = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = PeatlandSite.objects.filter(is_active=True).order_by("name")

    def clean_image(self):
        image = self.cleaned_data["image"]
        if image.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Ukuran gambar maksimum 10 MB.")
        return image
