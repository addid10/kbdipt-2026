from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("peatlandcovers", "0002_auto_20220516_2007"),
    ]

    operations = [
        migrations.CreateModel(
            name="PeatlandSite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("location", models.CharField(default="Banjarbaru, Kalimantan Selatan", max_length=255)),
                ("description", models.TextField(blank=True)),
                ("latitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True)),
                ("area_hectares", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("land_type", models.CharField(default="Lahan gambut", max_length=120)),
                ("protection_status", models.CharField(choices=[("protected", "Terlindungi"), ("managed", "Dikelola"), ("other", "Lainnya")], default="protected", max_length=20)),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to="peatland_sites/")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="VegetationPrediction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="vegetation_predictions/%Y/%m/")),
                ("vegetation_class", models.CharField(choices=[("dense", "Tinggi"), ("medium", "Sedang"), ("bare", "Terbuka/Bare")], max_length=20)),
                ("confidence", models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ("model_version", models.CharField(blank=True, max_length=120)),
                ("source", models.CharField(choices=[("model", "Model AI"), ("manual", "Manual")], default="model", max_length=20)),
                ("predicted_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="vegetation_predictions", to=settings.AUTH_USER_MODEL)),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vegetation_predictions", to="peatlandcovers.peatlandsite")),
            ],
            options={
                "ordering": ["-predicted_at"],
                "indexes": [models.Index(fields=["site", "-predicted_at"], name="vegpred_site_time_idx")],
            },
        ),
    ]
