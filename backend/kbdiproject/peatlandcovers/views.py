from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import redirect, render

from kbdiproject.views import staff_required

from .forms import PeatlandSiteForm, VegetationPredictionForm
from .models import PeatlandSite, VegetationPrediction
from .services import VegetationPredictionError, predict_vegetation


@staff_required
def index(request):
    site_form = PeatlandSiteForm(prefix="site")
    prediction_form = VegetationPredictionForm(prefix="prediction")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_site":
            site_form = PeatlandSiteForm(request.POST, request.FILES, prefix="site")
            if site_form.is_valid():
                site_form.save()
                messages.success(request, "Lahan berhasil ditambahkan.")
                return redirect("cover.index")
        elif action == "predict":
            prediction_form = VegetationPredictionForm(request.POST, request.FILES, prefix="prediction")
            if prediction_form.is_valid():
                image = prediction_form.cleaned_data["image"]
                try:
                    result = predict_vegetation(image)
                except VegetationPredictionError as exc:
                    prediction_form.add_error("image", str(exc))
                else:
                    VegetationPrediction.objects.create(
                        site=prediction_form.cleaned_data["site"],
                        image=image,
                        vegetation_class=result["vegetation_class"],
                        confidence=result["confidence"],
                        model_version=result["model_version"],
                        source=VegetationPrediction.Source.MODEL,
                        created_by=request.user,
                    )
                    messages.success(request, "Prediksi vegetasi berhasil diproses dan disimpan.")
                    return redirect("cover.index")

    sites = PeatlandSite.objects.prefetch_related(
        Prefetch(
            "vegetation_predictions",
            queryset=VegetationPrediction.objects.order_by("-predicted_at"),
        )
    )
    context = {
        "title": "Prediksi Vegetasi Lahan",
        "navbar": "vegetation",
        "site_form": site_form,
        "prediction_form": prediction_form,
        "sites": sites,
        "latest_predictions": VegetationPrediction.objects.select_related("site")[:12],
    }
    return render(request, "management/vegetation.html", context)
