from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PeatlandSite, VegetationPrediction
from .serializers import PeatlandSiteSerializer, VegetationPredictionSerializer
from .services import VegetationPredictionError, predict_vegetation


class PeatlandSiteListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PeatlandSiteSerializer
    queryset = PeatlandSite.objects.filter(is_active=True).order_by("name")


class VegetationPredictionListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VegetationPredictionSerializer

    def get_queryset(self):
        queryset = VegetationPrediction.objects.select_related("site")
        site_id = self.request.query_params.get("site")
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        return queryset[:100]


class VegetationPredictAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        site_id = request.data.get("site")
        image = request.FILES.get("image")
        if not site_id or not image:
            return Response(
                {"detail": "Both site and image are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            site = PeatlandSite.objects.get(pk=site_id, is_active=True)
        except PeatlandSite.DoesNotExist:
            return Response({"detail": "Peatland site not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = predict_vegetation(image)
        except VegetationPredictionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        prediction = VegetationPrediction.objects.create(
            site=site,
            image=image,
            vegetation_class=result["vegetation_class"],
            confidence=result["confidence"],
            model_version=result["model_version"],
            source=VegetationPrediction.Source.MODEL,
            created_by=request.user,
        )
        return Response(VegetationPredictionSerializer(prediction).data, status=status.HTTP_201_CREATED)
