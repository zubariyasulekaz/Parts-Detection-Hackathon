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

    With ``config.pad_to_square`` the image is first centered on a white
    square canvas (white to match the rembg background fill) so a long part
    like a shock absorber is not squashed into a different shape than the
    one the model saw in training. This must match how the deployed
    checkpoint was trained, which is why it is configuration, not a default.

    Args:
        image: Decoded PIL image (already background-removed upstream).
        config: Brain 1 configuration (``input_size``, ``pad_to_square``).

    Returns:
        An RGB PIL image of size ``(input_size, input_size)``.
    """
    rgb = image.convert("RGB")
    if config.pad_to_square and rgb.width != rgb.height:
        side = max(rgb.size)
        canvas = PILImage.new("RGB", (side, side), (255, 255, 255))
        canvas.paste(rgb, ((side - rgb.width) // 2, (side - rgb.height) // 2))
        rgb = canvas
    size = (config.input_size, config.input_size)
    return rgb.resize(size, PILImage.BILINEAR)
