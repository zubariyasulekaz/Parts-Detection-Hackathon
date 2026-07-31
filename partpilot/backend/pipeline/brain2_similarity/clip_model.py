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
        self._device: str = "cpu"

    @property
    def is_loaded(self) -> bool:
        """Whether the OpenCLIP model has been loaded into memory."""
        return self._model is not None

    @property
    def device(self) -> str:
        """The torch device the model is loaded on (``"cpu"`` or ``"cuda"``)."""
        return self._device

    def load(self) -> None:
        """Load the OpenCLIP model and preprocessing transform.

        ``open_clip``/``torch`` are imported lazily so this module can be
        imported in environments where they are not installed.
        """
        try:
            import open_clip  # noqa: PLC0415
            import torch  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ModelNotLoaded(
                "open_clip_torch / torch are not installed; cannot load the OpenCLIP model."
            ) from exc

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            self._model_name, pretrained=self._pretrained
        )
        model = model.to(self._device)
        model.eval()
        self._model = model
        self._preprocess = preprocess
        logger.info(
            "Loaded OpenCLIP model %s/%s on %s",
            self._model_name,
            self._pretrained,
            self._device,
        )

    def get(self) -> tuple[Any, Any]:
        """Return the `(model, preprocess)` pair, once loaded.

        Raises:
            backend.core.exceptions.ModelNotLoaded: If `load()` has not
                been called successfully yet.
        """
        if self._model is None or self._preprocess is None:
            raise ModelNotLoaded("OpenCLIP model has not been loaded.")
        return self._model, self._preprocess
