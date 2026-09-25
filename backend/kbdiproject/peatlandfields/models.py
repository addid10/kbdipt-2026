from django.db import models

from peatlandcovers.models import PeatlandCover


class PeatlandField(models.Model):
    """Legacy field-observation model retained for database compatibility."""

    water_level = models.FloatField(null=True)
    max_air_temperature = models.FloatField(null=True)
    date = models.DateField(auto_now_add=True)
    peatland_cover = models.ForeignKey(PeatlandCover, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.peatland_cover.name} - {self.date}"

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Legacy peatland field observation"
        verbose_name_plural = "Legacy peatland field observations"
