"""Image pre-processing for the Brain 1 classifier.

Background removal is applied once upstream (in the orchestrator) so the
classifier and the similarity search see the same cleaned image, so this
step only resizes to the model's input size. EfficientNet normalization
(``efficientnet.preprocess_input``) is baked into the saved model graph
by the training notebook, so it must NOT be re-applied here.
"""

from PIL import Image as PILImage
from PIL.Image import Image

from backend.pipeline.brain1_classifier.config import Brain1Config


def preprocess_image(image: Image, config: Brain1Config) -> Image:
    """Resize a (background-removed) image to the classifier's input size.

    Args:
        image: Decoded PIL image (already background-removed upstream).
        config: Brain 1 configuration (``input_size``).

    Returns:
        An RGB PIL image of size ``(input_size, input_size)``.
    """
    size = (config.input_size, config.input_size)
    return image.convert("RGB").resize(size, PILImage.BILINEAR)
