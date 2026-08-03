"""Swappable image-embedding backends for Brain 2.

Brain 2 turns a photo into a vector and looks for the nearest catalog vector.
Which model produces that vector is a separate question from the rest of the
pipeline, so the choice lives here behind one interface.

Three families are supported, all open weights:

``openclip``   OpenCLIP (LAION, MIT). Trained to align images with text.
``siglip``     SigLIP (Google, Apache 2.0). Same idea, better training loss.
``dinov2``     DINOv2 (Meta, Apache 2.0). Self-supervised on images only, so it
               is tuned for "is this the same object" rather than "what is this
               called" - usually the stronger choice for catalog matching.

Backends can also be combined with ``+``::

    dinov2+siglip

Each model's vector is L2-normalized, the vectors are concatenated, and the
result is normalized again. Cosine similarity on that combined vector is the
average of the individual cosine similarities, so the models effectively vote.
This helps when they make different mistakes, and hurts when one member is much
weaker than the others - worth measuring rather than assuming.

Selected via ``EMBEDDING_BACKEND`` in settings. Changing it invalidates existing
FAISS indexes: vectors from different models are not comparable, so rebuild.
"""

from typing import Any

import numpy as np
from PIL.Image import Image

from backend.config.settings import get_settings
from backend.core.exceptions import EmbeddingError, ModelNotLoaded
from backend.core.logging import get_logger

logger = get_logger(__name__)


def _unit(vector: np.ndarray) -> np.ndarray:
    """L2-normalize, leaving an all-zero vector alone."""
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def _torch() -> Any:
    try:
        import torch  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise EmbeddingError("torch is not installed; cannot generate embeddings.") from exc
    return torch


class EmbeddingBackend:
    """One image encoder. Loads lazily on first use."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._model: Any | None = None
        self._preprocess: Any | None = None
        self._device: str = "cpu"

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:  # pragma: no cover - subclass responsibility
        raise NotImplementedError

    def encode(self, image: Image) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError

    def _pick_device(self) -> str:
        torch = _torch()
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        return self._device


class OpenClipBackend(EmbeddingBackend):
    """OpenCLIP image tower (the original Brain 2 backend)."""

    def __init__(self, model_name: str | None = None, pretrained: str | None = None) -> None:
        super().__init__("openclip")
        settings = get_settings()
        self._model_name = model_name or settings.OPENCLIP_MODEL_NAME
        self._pretrained = pretrained or settings.OPENCLIP_PRETRAINED

    def load(self) -> None:
        try:
            import open_clip  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ModelNotLoaded("open_clip_torch is not installed.") from exc

        device = self._pick_device()
        model, _, preprocess = open_clip.create_model_and_transforms(
            self._model_name, pretrained=self._pretrained
        )
        self._model = model.to(device).eval()
        self._preprocess = preprocess
        logger.info("Loaded OpenCLIP %s/%s on %s", self._model_name, self._pretrained, device)

    def encode(self, image: Image) -> np.ndarray:
        torch = _torch()
        if not self.is_loaded:
            self.load()
        tensor = self._preprocess(image.convert("RGB")).unsqueeze(0).to(self._device)
        with torch.no_grad():
            out = self._model.encode_image(tensor)
        return _unit(out.squeeze(0).cpu().numpy().astype(np.float32))


class HuggingFaceVisionBackend(EmbeddingBackend):
    """SigLIP / DINOv2 via ``transformers``.

    Both expose an image encoder through ``AutoModel``; the difference is only
    which pooled output represents the image, handled in ``encode``.
    """

    def __init__(self, name: str, model_id: str) -> None:
        super().__init__(name)
        self._model_id = model_id

    def load(self) -> None:
        try:
            from transformers import AutoImageProcessor, AutoModel  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ModelNotLoaded("transformers is not installed.") from exc

        device = self._pick_device()
        self._preprocess = AutoImageProcessor.from_pretrained(self._model_id)
        self._model = AutoModel.from_pretrained(self._model_id).to(device).eval()
        logger.info("Loaded %s (%s) on %s", self.name, self._model_id, device)

    def encode(self, image: Image) -> np.ndarray:
        torch = _torch()
        if not self.is_loaded:
            self.load()
        inputs = self._preprocess(images=image.convert("RGB"), return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            if hasattr(self._model, "get_image_features"):
                # SigLIP / CLIP-style: a dedicated image-feature head.
                out = self._model.get_image_features(**inputs)
            else:
                # DINOv2: pooled CLS token summarises the image.
                out = self._model(**inputs)
                out = getattr(out, "pooler_output", None)
                if out is None:
                    out = self._model(**inputs).last_hidden_state[:, 0]
        return _unit(out.squeeze(0).cpu().numpy().astype(np.float32))


class CompositeBackend(EmbeddingBackend):
    """Concatenates several backends so their similarity scores average."""

    def __init__(self, backends: list[EmbeddingBackend]) -> None:
        super().__init__("+".join(b.name for b in backends))
        self._backends = backends

    @property
    def is_loaded(self) -> bool:
        return all(b.is_loaded for b in self._backends)

    def load(self) -> None:
        for backend in self._backends:
            backend.load()

    def encode(self, image: Image) -> np.ndarray:
        parts = [backend.encode(image) for backend in self._backends]
        # Each part is already unit length; scaling by 1/sqrt(n) before
        # concatenating makes the combined dot product the mean of the parts.
        scale = 1.0 / np.sqrt(len(parts))
        return _unit(np.concatenate([p * scale for p in parts]).astype(np.float32))


#: Short names accepted in ``EMBEDDING_BACKEND``.
_HF_MODELS = {
    "dinov2": "facebook/dinov2-base",
    "dinov2-small": "facebook/dinov2-small",
    "dinov2-base": "facebook/dinov2-base",
    "dinov2-large": "facebook/dinov2-large",
    "siglip": "google/siglip-base-patch16-224",
    "siglip-base": "google/siglip-base-patch16-224",
    "siglip-large": "google/siglip-large-patch16-256",
    "siglip-so400m": "google/siglip-so400m-patch14-384",
}


def _build_one(name: str) -> EmbeddingBackend:
    key = name.strip().lower()
    if key in {"openclip", "clip"}:
        return OpenClipBackend()
    if key.startswith("openclip:"):
        # openclip:ViT-L-14:laion2b_s32b_b82k
        parts = name.split(":")
        model = parts[1] if len(parts) > 1 else None
        pretrained = parts[2] if len(parts) > 2 else None
        return OpenClipBackend(model, pretrained)
    if key in _HF_MODELS:
        family = "dinov2" if key.startswith("dinov2") else "siglip"
        return HuggingFaceVisionBackend(key, _HF_MODELS[key])
    if "/" in name:  # any HuggingFace model id
        family = "dinov2" if "dino" in key else "siglip"
        return HuggingFaceVisionBackend(family, name)
    raise EmbeddingError(
        f"Unknown embedding backend '{name}'. "
        f"Expected one of: openclip, {', '.join(sorted(_HF_MODELS))}, "
        "or a HuggingFace model id."
    )


def build_backend(spec: str | None = None) -> EmbeddingBackend:
    """Build the backend named by ``spec`` (default: the configured one).

    Combine models with ``+``, e.g. ``"dinov2+siglip"``.
    """
    spec = spec or get_settings().EMBEDDING_BACKEND
    names = [n for n in spec.split("+") if n.strip()]
    if not names:
        raise EmbeddingError("EMBEDDING_BACKEND is empty.")
    if len(names) == 1:
        return _build_one(names[0])
    return CompositeBackend([_build_one(n) for n in names])
