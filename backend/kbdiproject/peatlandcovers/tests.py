from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .models import PeatlandSite
from .services import MODEL_CLASS_ORDER, predict_vegetation


class PeatlandSiteTests(TestCase):
    def test_site_code_is_unique(self):
        PeatlandSite.objects.create(name="Site A", code="site-a")
        self.assertEqual(PeatlandSite.objects.count(), 1)


class VegetationModelSmokeTests(TestCase):
    def test_checkpoint_can_run_one_rgb_image(self):
        buffer = BytesIO()
        Image.new("RGB", (224, 224), (100, 130, 90)).save(buffer, format="JPEG")
        upload = SimpleUploadedFile("sample.jpg", buffer.getvalue(), content_type="image/jpeg")

        result = predict_vegetation(upload)

        self.assertIn(result["vegetation_class"], MODEL_CLASS_ORDER)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
