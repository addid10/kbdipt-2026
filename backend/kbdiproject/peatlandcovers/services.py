"""Vegetation inference service.

The classifier label order is preserved from the original project checkpoint:
index 0 = dense/high vegetation, index 1 = bare, index 2 = medium vegetation.
"""

from functools import lru_cache
from io import BytesIO

from django.conf import settings
from PIL import Image, UnidentifiedImageError
import torch
from torchvision import transforms

from neuralnetworks.ShuffleNet2 import ShuffleNet2


MODEL_CLASS_ORDER = ("dense", "bare", "medium")


class VegetationPredictionError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_vegetation_model():
    model_path = settings.VEGETATION_MODEL_PATH
    if not model_path.exists():
        raise VegetationPredictionError(f"Model checkpoint not found: {model_path}")

    model = ShuffleNet2(num_classes=3, input_size=224, net_type=1)
    state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    return model


def _preprocess_image(image_bytes: bytes):
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            preprocessing = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            )
            return preprocessing(image).unsqueeze(0)
    except (UnidentifiedImageError, OSError) as exc:
        raise VegetationPredictionError("Uploaded file is not a valid image.") from exc


def predict_vegetation(uploaded_file):
    """Return an English class key and confidence score for one uploaded image."""

    max_bytes = settings.MAX_VEGETATION_IMAGE_SIZE_MB * 1024 * 1024
    file_size = getattr(uploaded_file, "size", None)
    if file_size is not None and file_size > max_bytes:
        raise VegetationPredictionError(
            f"Uploaded image exceeds {settings.MAX_VEGETATION_IMAGE_SIZE_MB} MB."
        )

    uploaded_file.seek(0)
    image_bytes = uploaded_file.read(max_bytes + 1)
    if len(image_bytes) > max_bytes:
        raise VegetationPredictionError(
            f"Uploaded image exceeds {settings.MAX_VEGETATION_IMAGE_SIZE_MB} MB."
        )
    uploaded_file.seek(0)
    if not image_bytes:
        raise VegetationPredictionError("Uploaded image is empty.")

    input_batch = _preprocess_image(image_bytes)
    model = get_vegetation_model()

    with torch.inference_mode():
        logits = model(input_batch)
        probabilities = torch.softmax(logits[0], dim=0)
        confidence, class_index = torch.max(probabilities, dim=0)

    return {
        "vegetation_class": MODEL_CLASS_ORDER[int(class_index.item())],
        "confidence": float(confidence.item()),
        "model_version": settings.VEGETATION_MODEL_VERSION,
    }
