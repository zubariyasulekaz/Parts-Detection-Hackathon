"""OpenCLIP model wrapper.

TODO: Implement loading of an OpenCLIP checkpoint (`open_clip.create_model_and_transforms`)
and expose the image encoder used by `embedding_generator.py`.
"""

from typing import Any

from backend.config.settings import get_settings
from backend.core.exceptions import ModelNotLoaded
from backend.core.logging import get_logger

logger = get_logger(__name__)


class CLIPModel:
    """Thin wrapper around an OpenCLIP model + preprocessing transform."""

    def __init__(self, model_name: str | None = None, pretrained: str | None = None) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.OPENCLIP_MODEL_NAME
        self._pretrained = pretrained or settings.OPENCLIP_PRETRAINED
        self._model: Any | None = None
        self._preprocess: Any | None = None

    @property
    def is_loaded(self) -> bool:
        """Whether the OpenCLIP model has been loaded into memory."""
        return self._model is not None

    def load(self) -> None:
        """Load the OpenCLIP model and preprocessing transform.

        TODO: Implement via `open_clip.create_model_and_transforms(
        self._model_name, pretrained=self._pretrained)`.
        """
        raise NotImplementedError("OpenCLIP model loading is not implemented yet.")

    def get(self) -> tuple[Any, Any]:
        """Return the `(model, preprocess)` pair, once loaded.

        Raises:
            backend.core.exceptions.ModelNotLoaded: If `load()` has not
                been called successfully yet.
        """
        if self._model is None or self._preprocess is None:
            raise ModelNotLoaded("OpenCLIP model has not been loaded.")
        return self._model, self._preprocess
