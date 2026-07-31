"""Unit tests for Brain 1 helpers that don't require TensorFlow.

Model inference itself needs a trained ``.keras`` checkpoint + tensorflow,
so it is exercised in Colab/deploy rather than here.
"""

from PIL import Image

from backend.pipeline.brain1_classifier.config import Brain1Config
from backend.pipeline.brain1_classifier.labels import resolve_catalog_category
from backend.pipeline.brain1_classifier.preprocess import preprocess_image


def test_resolve_catalog_category_maps_classifier_labels() -> None:
    assert resolve_catalog_category("brake_pad") == "Brake Pads"
    assert resolve_catalog_category("oil_filter") == "Oil Filter"
    # Case/spacing-insensitive via slug.
    assert resolve_catalog_category("Brake Pad") == "Brake Pads"


def test_resolve_catalog_category_passes_through_unknown() -> None:
    assert resolve_catalog_category("Timing Belt") == "Timing Belt"


def test_preprocess_image_resizes_to_input_size() -> None:
    config = Brain1Config(model_path="unused", input_size=224, confidence_threshold=0.5)
    out = preprocess_image(Image.new("RGB", (640, 480)), config)
    assert out.size == (224, 224)
    assert out.mode == "RGB"
