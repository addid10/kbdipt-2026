from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("peatlandcovers", "0003_production_models"),
        ("kbdis", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="KBDIReading",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("observed_at", models.DateTimeField()),
                ("rainfall_today_mm", models.FloatField(validators=[django.core.validators.MinValueValidator(0.0)])),
                ("rainfall_yesterday_mm", models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0)])),
                ("max_temperature_c", models.FloatField()),
                ("water_table_depth_mm", models.FloatField(blank=True, help_text="Observed water table depth below the peat surface. Stored for monitoring; not substituted for wc in the KBDIpt equation.", null=True)),
                ("previous_kbdi", models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0)])),
                ("rain_event_accumulation_mm", models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0)])),
                ("effective_rainfall_mm", models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0)])),
                ("drought_factor", models.FloatField(default=0.0)),
                ("kbdi", models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(400.0)])),
                ("level", models.CharField(choices=[("low", "Low"), ("moderate", "Moderat"), ("high", "High"), ("extreme", "Extreme")], max_length=20)),
                ("formula_profile", models.CharField(choices=[("novitasari_2019", "Novitasari et al. (2019) - tropical peatland")], default="novitasari_2019", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kbdi_readings", to=settings.AUTH_USER_MODEL)),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kbdi_readings", to="peatlandcovers.peatlandsite")),
            ],
            options={
                "ordering": ["-observed_at", "-id"],
                "indexes": [
                    models.Index(fields=["site", "-observed_at"], name="kbdi_site_time_idx"),
                    models.Index(fields=["level", "-observed_at"], name="kbdi_level_time_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="AlertEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("severity", models.CharField(choices=[("high", "High"), ("extreme", "Extreme")], max_length=20)),
                ("status", models.CharField(choices=[("active", "Aktif"), ("cleared", "Selesai")], default="active", max_length=20)),
                ("message", models.CharField(max_length=255)),
                ("triggered_at", models.DateTimeField()),
                ("cleared_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reading", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alert_events", to="kbdis.kbdireading")),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_events", to="peatlandcovers.peatlandsite")),
            ],
            options={
                "ordering": ["-triggered_at", "-id"],
                "indexes": [
                    models.Index(fields=["site", "status"], name="alert_site_status_idx"),
                    models.Index(fields=["severity", "-triggered_at"], name="alert_sev_time_idx"),
                ],
                "constraints": [models.UniqueConstraint(condition=models.Q(status="active"), fields=("site",), name="one_active_alert_per_site")],
            },
        ),
    ]
