from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from datetime import timedelta

from peatlandcovers.models import PeatlandSite

from .models import AlertEvent, KBDIReading
from .serializers import KBDIReadingCreateSerializer
from .services import (
    calculate_effective_rainfall,
    classify_kbdi,
    create_kbdi_reading,
)


class KBDIptFormulaTests(SimpleTestCase):
    def test_peatland_thresholds(self):
        cases = [
            (0, KBDIReading.Level.LOW),
            (200, KBDIReading.Level.LOW),
            (200.01, KBDIReading.Level.MODERATE),
            (300, KBDIReading.Level.MODERATE),
            (300.01, KBDIReading.Level.HIGH),
            (350, KBDIReading.Level.HIGH),
            (350.01, KBDIReading.Level.EXTREME),
            (400, KBDIReading.Level.EXTREME),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(classify_kbdi(value), expected)

    def test_first_5_point_1_mm_of_continuous_rain_is_ignored(self):
        effective_day_one, accumulation = calculate_effective_rainfall(4.7, 0)
        effective_day_two, accumulation = calculate_effective_rainfall(4.8, accumulation)

        self.assertEqual(effective_day_one, 0)
        self.assertAlmostEqual(effective_day_two, 4.4, places=6)
        self.assertAlmostEqual(accumulation, 9.5, places=6)


class PreviousKBDIResolutionTests(TestCase):
    def setUp(self):
        self.site = PeatlandSite.objects.create(
            name="Liang Anggang Block 1",
            code="liang-anggang-block-1",
        )
        self.time_one = timezone.now() - timedelta(hours=24)
        self.time_two = timezone.now()

    def test_first_reading_requires_initial_kbdi(self):
        serializer = KBDIReadingCreateSerializer(
            data={
                "site": self.site.id,
                "observed_at": self.time_one,
                "rainfall_today_mm": 0,
                "rainfall_yesterday_mm": 0,
                "max_temperature_c": 30,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("initial_kbdi", serializer.errors)

    def test_second_reading_uses_previous_kbdi_automatically(self):
        first = create_kbdi_reading(
            site=self.site,
            observed_at=self.time_one,
            rainfall_today_mm=0,
            rainfall_yesterday_mm=0,
            max_temperature_c=30,
            initial_kbdi=250,
        )
        second = create_kbdi_reading(
            site=self.site,
            observed_at=self.time_two,
            rainfall_today_mm=0,
            rainfall_yesterday_mm=0,
            max_temperature_c=30,
        )
        self.assertAlmostEqual(second.previous_kbdi, first.kbdi, places=6)

    def test_initial_value_cannot_override_existing_previous_reading(self):
        first = create_kbdi_reading(
            site=self.site,
            observed_at=self.time_one,
            rainfall_today_mm=0,
            rainfall_yesterday_mm=0,
            max_temperature_c=30,
            initial_kbdi=220,
        )
        second = create_kbdi_reading(
            site=self.site,
            observed_at=self.time_two,
            rainfall_today_mm=0,
            rainfall_yesterday_mm=0,
            max_temperature_c=30,
            initial_kbdi=399,
        )
        self.assertAlmostEqual(second.previous_kbdi, first.kbdi, places=6)


class AlertLifecycleTests(TestCase):
    def setUp(self):
        self.site = PeatlandSite.objects.create(
            name="Liang Anggang Block 1",
            code="liang-anggang-block-1",
        )
        self.base_time = timezone.now() - timedelta(hours=48)

    def test_high_extreme_and_clear_lifecycle(self):
        high = create_kbdi_reading(
            site=self.site,
            observed_at=self.base_time,
            rainfall_today_mm=0,
            rainfall_yesterday_mm=0,
            max_temperature_c=30,
            initial_kbdi=320,
        )
        self.assertEqual(high.level, KBDIReading.Level.HIGH)
        self.assertTrue(high.alarm_active)
        self.assertEqual(
            AlertEvent.objects.filter(site=self.site, status=AlertEvent.Status.ACTIVE).count(),
            1,
        )

        extreme = create_kbdi_reading(
            site=self.site,
            observed_at=self.base_time + timedelta(hours=24),
            rainfall_today_mm=0,
            rainfall_yesterday_mm=0,
            max_temperature_c=70,
        )
        self.assertEqual(extreme.level, KBDIReading.Level.EXTREME)
        self.assertEqual(
            AlertEvent.objects.filter(site=self.site, status=AlertEvent.Status.ACTIVE).count(),
            1,
        )
        self.assertEqual(
            AlertEvent.objects.get(site=self.site, status=AlertEvent.Status.ACTIVE).severity,
            KBDIReading.Level.EXTREME,
        )

        cleared = create_kbdi_reading(
            site=self.site,
            observed_at=self.base_time + timedelta(hours=48),
            rainfall_today_mm=100,
            rainfall_yesterday_mm=0,
            max_temperature_c=25,
        )
        self.assertIn(cleared.level, {KBDIReading.Level.LOW, KBDIReading.Level.MODERATE})
        self.assertFalse(cleared.alarm_active)
        self.assertFalse(
            AlertEvent.objects.filter(site=self.site, status=AlertEvent.Status.ACTIVE).exists()
        )
