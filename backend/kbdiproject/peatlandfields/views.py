from django.http import JsonResponse

from .models import PeatlandField
from .serializers import PeatlandFieldSerializer


def peatland_field_list(request):
    """Legacy read-only endpoint kept for backward compatibility."""
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    observations = PeatlandField.objects.all()
    serializer = PeatlandFieldSerializer(observations, many=True)
    return JsonResponse(serializer.data, safe=False)
