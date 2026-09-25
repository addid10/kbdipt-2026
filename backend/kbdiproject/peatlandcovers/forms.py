from django import forms

from .models import PeatlandSite


class PeatlandSiteForm(forms.ModelForm):
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
