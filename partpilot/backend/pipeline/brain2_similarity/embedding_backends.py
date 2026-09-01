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

from pathlib import Path
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
        self._load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:  # pragma: no cover - subclass responsibility
        raise NotImplementedError

    def ensure_loaded(self) -> None:
        """Load once, and remember a failure instead of retrying it.

        Weights are fetched from Hugging Face on first use, and that fetch
        stalls for minutes behind HTTP retries when the CDN is unreachable.
        Backends are cached for the life of the process (see `BackendCache`),
        so without this every request would pay that stall again. Restart the
        backend to retry once the download works.
        """
        if self.is_loaded:
            return
        if self._load_error is not None:
            raise ModelNotLoaded(self._load_error)
        try:
            self.load()
        except Exception as exc:  # noqa: BLE001
            self._load_error = (
                f"Could not load the '{self.name}' embedding model: {exc}. "
                "Restart the backend to retry."
            )
            logger.warning(self._load_error)
            raise ModelNotLoaded(self._load_error) from exc

    def encode(self, image: Image) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError

    def _pick_device(self) -> str:
        torch = _torch()
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        return self._device


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
        self.ensure_loaded()
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
            backend.ensure_loaded()

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


def _family_of(name: str, key: str) -> str:
    """Which backend family a model id or local directory belongs to.

    Read from the model's own config rather than guessed from its name. The name
    is not reliable evidence: a fine-tuned DINOv2 saved to ``out/run-3`` contains
    no "dino", and would be recorded as siglip. Encoding would still be correct -
    the encoder branches on the model, not this label - but the wrong backend
    name is written into the index metadata, and that is what the runtime checks
    a query against.

    Falls back to the name heuristic when the config cannot be read (offline, or
    a private id), which is no worse than what it replaces.
    """
    try:
        from transformers import AutoConfig  # noqa: PLC0415

        model_type = (getattr(AutoConfig.from_pretrained(name), "model_type", "") or "").lower()
        if model_type:
            return "dinov2" if "dino" in model_type else "siglip"
    except Exception:  # noqa: BLE001 - any failure just means fall back
        logger.debug("Could not read config for %s; guessing family from the name.", name)
    return "dinov2" if "dino" in key else "siglip"


def _build_one(name: str) -> EmbeddingBackend:
    key = name.strip().lower()
    if key in _HF_MODELS:
        return HuggingFaceVisionBackend(key, _HF_MODELS[key])
    if "/" in name or Path(name).is_dir():  # a HuggingFace model id, or a local directory
        return HuggingFaceVisionBackend(_family_of(name, key), name)
    raise EmbeddingError(
        f"Unknown embedding backend '{name}'. "
        f"Expected one of: {', '.join(sorted(_HF_MODELS))}, "
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


def backend_for_category(category: str) -> str:
    """Which backend spec a category should use.

    RigidHitch files every product under one sentinel category served by one
    index, so this is the configured default for everything. Kept as a function
    rather than inlined because the index records the model that built it and
    `SimilaritySearchService` prefers that over the setting - this is only the
    fallback for an index that never recorded one.
    """
    return get_settings().EMBEDDING_BACKEND


def no_match_threshold(backend: str | None) -> float:
    """The similarity below which a top match is not a plausible answer.

    Keyed per backend spec because score distributions differ between models -
    two encoders compress cosine space differently, so one global value cannot
    serve both. Falls back to the configured default for unknown or composite
    specs and for older indexes that never recorded their backend.
    """
    settings = get_settings()
    if backend:
        wanted = backend.strip().lower()
        for name, value in settings.NO_MATCH_THRESHOLDS.items():
            if name.strip().lower() == wanted:
                return value
    return settings.NO_MATCH_THRESHOLD_DEFAULT


class BackendCache:
    """Builds each backend once and reuses it.

    With per-category backends a single request may touch more than one model,
    and loading a vision transformer is slow, so keep them around.
    """

    def __init__(self) -> None:
        self._backends: dict[str, EmbeddingBackend] = {}

    def get(self, spec: str) -> EmbeddingBackend:
        if spec not in self._backends:
            self._backends[spec] = build_backend(spec)
        return self._backends[spec]
