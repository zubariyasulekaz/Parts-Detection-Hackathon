"""Application settings, sourced from environment variables / `.env`.

Uses `pydantic-settings` so configuration is validated at startup instead
of failing deep inside some pipeline stage at inference time.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config.paths import (
    CATALOG_CSV_PATH,
    CLASSIFIER_MODEL_DIR,
    FAISS_MODEL_DIR,
    UPLOADS_DIR,
)


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
    APP_NAME: str = "PartPilot"
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
    MODEL_PATH: str = str(CLASSIFIER_MODEL_DIR)
    CLIP_MODEL_PATH: str = ""
    FAISS_PATH: str = str(FAISS_MODEL_DIR)
    CATALOG_PATH: str = str(CATALOG_CSV_PATH)
    UPLOAD_PATH: str = str(UPLOADS_DIR)

    # --- Brain 1: classifier ---------------------------------------------------------------
    CLASSIFIER_INPUT_SIZE: int = 224
    CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.5

    # --- Brain 2: similarity search ---------------------------------------------------------------
    OPENCLIP_MODEL_NAME: str = "ViT-B-32"
    OPENCLIP_PRETRAINED: str = "openai"
    FAISS_TOP_K: int = 10

    # --- Brain 4: reasoning (future) ---------------------------------------------------------------
    HF_TOKEN: str | None = None
    LLM_MODEL_NAME: str | None = None

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
