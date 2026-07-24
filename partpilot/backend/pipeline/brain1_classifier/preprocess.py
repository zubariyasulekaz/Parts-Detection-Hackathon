"""Image pre-processing for the Brain 1 classifier.

TODO: Implement the actual EfficientNet pre-processing pipeline
(resize, center-crop, normalization, background removal via `rembg`
if required, etc.).
"""

from PIL.Image import Image

from backend.pipeline.brain1_classifier.config import Brain1Config


def preprocess_image(image: Image, config: Brain1Config) -> Image:
    """Prepare a raw uploaded image for classifier inference.

    Args:
        image: Raw decoded PIL image, as received from the upload.
        config: Brain 1 configuration (input size, etc.).

    Returns:
        A pre-processed PIL image ready to be passed to the model.

    TODO:
        - Resize/center-crop to `config.input_size`.
        - Apply EfficientNet-specific normalization.
        - Optionally strip backgrounds with `rembg` before classification.
    """
    raise NotImplementedError("Brain 1 preprocessing is not implemented yet.")
