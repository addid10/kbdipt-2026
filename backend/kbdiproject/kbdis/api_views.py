from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from peatlandcovers.models import PeatlandSite

from .models import AlertEvent, KBDIReading
from .serializers import AlertEventSerializer, KBDIReadingCreateSerializer, KBDIReadingSerializer


class KBDIReadingListCreateAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = KBDIReading.objects.select_related("site")
        site_id = request.query_params.get("site")
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        return Response(KBDIReadingSerializer(queryset[:200], many=True).data)

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Staff permission is required to create KBDI readings."}, status=403)
        serializer = KBDIReadingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        reading = serializer.save()
        return Response(KBDIReadingSerializer(reading).data, status=status.HTTP_201_CREATED)


class EWSStatusAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, site_id):
        site = get_object_or_404(PeatlandSite, pk=site_id, is_active=True)
        reading = site.kbdi_readings.first()
        active_alert = site.alert_events.filter(status=AlertEvent.Status.ACTIVE).first()
        prediction = site.vegetation_predictions.first()

        return Response(
            {
                "site": {
                    "id": site.id,
                    "code": site.code,
                    "name": site.name,
                    "location": site.location,
                },
                "status": None if not reading else {
                    "reading_id": reading.id,
                    "observed_at": reading.observed_at,
                    "kbdi": round(reading.kbdi, 2),
                    "level": reading.level,
                    "level_label": reading.get_level_display(),
                    "alarm": reading.alarm_active,
                    "alarm_level": 2 if reading.level == KBDIReading.Level.EXTREME else (1 if reading.level == KBDIReading.Level.HIGH else 0),
                },
                "vegetation": None if not prediction else {
                    "class": prediction.vegetation_class,
                    "label": prediction.get_vegetation_class_display(),
                    "confidence": round(prediction.confidence, 4),
                    "predicted_at": prediction.predicted_at,
                },
                "active_alert": None if not active_alert else AlertEventSerializer(active_alert).data,
            }
        )


class ActiveAlertListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AlertEventSerializer

    def get_queryset(self):
        queryset = AlertEvent.objects.select_related("site", "reading")
        status_filter = self.request.query_params.get("status", AlertEvent.Status.ACTIVE)
        if status_filter in {AlertEvent.Status.ACTIVE, AlertEvent.Status.CLEARED}:
            queryset = queryset.filter(status=status_filter)
        site_id = self.request.query_params.get("site")
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        return queryset[:200]
