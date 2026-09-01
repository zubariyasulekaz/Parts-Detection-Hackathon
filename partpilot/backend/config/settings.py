"""Application settings, sourced from environment variables / `.env`.

Uses `pydantic-settings` so configuration is validated at startup instead
of failing deep inside some pipeline stage at inference time.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config.paths import UPLOADS_DIR


class Settings(BaseSettings):
    """Strongly-typed application configuration.

    Values are read from environment variables first, then from a local
    `.env` file (see `.env.example` for the full list of supported keys).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- application ---------------------------------------------------------------
    APP_NAME: str = "RigidHitch Part Finder"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = True

    # --- server ---------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    # --- logging ---------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    # --- filesystem paths (overridable via env) ---------------------------------------------------------------
    UPLOAD_PATH: str = str(UPLOADS_DIR)

    # --- catalogue database ---------------------------------------------------------------
    # Unset means the catalogue routes fail with a clear message rather than
    # silently serving matches with no product details attached.
    RIGIDHITCH_DATABASE_URL: str | None = None
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # --- search index ---------------------------------------------------------------
    RIGIDHITCH_FAISS_PATH: str = "backend/models/faiss_rigidhitch"
    # The sentinel category the single flat index is filed under. There is no
    # classifier - 50.9% of products sit in more than one top-level category,
    # so there is no single correct route for a query - and every search goes
    # to this one index instead.
    RIGIDHITCH_CATEGORY: str = "rigidhitch"

    # --- product images ---------------------------------------------------------------
    # Prepended to each product's stored relative image path to make a URL a
    # browser can load. Point it at the client's own CDN in production; the
    # local static mount is only for demos.
    RIGIDHITCH_IMAGE_BASE_URL: str = "http://localhost:8000/rigidhitch-images"
    # Served from disk at RIGIDHITCH_IMAGE_BASE_URL when set. Unset in
    # production, where the client's CDN serves them instead.
    RIGIDHITCH_IMAGE_DIR: str | None = None

    # --- embedding model ---------------------------------------------------------------
    # Which model turns an image into a vector: one of the shorthand names in
    # `embedding_backends._HF_MODELS`, a HuggingFace model id, or a local
    # directory. The shipped index was built by a fine-tuned checkpoint and
    # records its own path, which takes precedence over this - so this is only
    # the fallback for an index that never recorded one. Changing it invalidates
    # the index; rebuild after switching.
    EMBEDDING_BACKEND: str = "dinov2"
    FAISS_TOP_K: int = 10
    # Average the embedding of the image and its mirror at query/build time.
    # Cheap test-time augmentation; both sides must use the same setting, so
    # rebuild the index after changing it.
    EMBEDDING_TTA: bool = True
    # Below this top similarity the search reports "no catalog match" and skips
    # catalogue resolution, instead of confidently naming the nearest wrong
    # part. Scores are cosine against a per-SKU centroid (see
    # FaissIndex.search), keyed per embedding backend because two models
    # compress cosine space differently and one global value cannot serve both.
    #
    # Calibrated with scripts/analyze_index_vectors.py over the stored index
    # vectors (rembg + TTA, leave-one-out). Policy: refusing is better than
    # guessing, so this sits at ~1.5% correct-match rejection rather than 0%.
    NO_MATCH_THRESHOLDS: dict[str, float] = {
        "dinov2": 0.48,
    }
    NO_MATCH_THRESHOLD_DEFAULT: float = 0.48

    # --- startup ---------------------------------------------------------------
    # Load the model and index during startup instead of inside the first
    # request, which otherwise pays a 20-60s cold start. On a server that cost
    # lands on whoever opens the link first.
    WARM_MODELS_ON_STARTUP: bool = True

    # --- uploads ---------------------------------------------------------------
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: list[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"]
    )

    # --- security ---------------------------------------------------------------
    API_KEY: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` singleton.

    `lru_cache` ensures the environment/`.env` is only parsed once per
    process while still allowing dependency-injection style overrides in
    tests via `get_settings.cache_clear()`.
    """
    return Settings()
