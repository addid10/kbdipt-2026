from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .forms import PeatlandSiteForm
from .models import PeatlandSite
from .services import MODEL_CLASS_ORDER, predict_vegetation


class PeatlandSiteTests(TestCase):
    def test_site_code_is_unique(self):
        PeatlandSite.objects.create(name="Site A", code="site-a")
        self.assertEqual(PeatlandSite.objects.count(), 1)

    def test_full_precision_coordinates_are_accepted_and_rounded(self):
        form = PeatlandSiteForm(
            data={
                "name": "Hutan Lindung Liang Anggang",
                "code": "la01",
                "location": "Banjarbaru, Kalimantan Selatan",
                "latitude": "-3.4165610719508575",
                "longitude": "114.70704292237144",
                "land_type": "Lahan Gambut",
                "protection_status": PeatlandSite.ProtectionStatus.PROTECTED,
                "is_active": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        site = form.save()
        self.assertEqual(str(site.latitude), "-3.4165611")
        self.assertEqual(str(site.longitude), "114.7070429")


class VegetationModelSmokeTests(TestCase):
    def test_checkpoint_can_run_one_rgb_image(self):
        buffer = BytesIO()
        Image.new("RGB", (224, 224), (100, 130, 90)).save(buffer, format="JPEG")
        upload = SimpleUploadedFile("sample.jpg", buffer.getvalue(), content_type="image/jpeg")

        result = predict_vegetation(upload)

        self.assertIn(result["vegetation_class"], MODEL_CLASS_ORDER)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
