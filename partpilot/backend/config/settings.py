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

    # --- database (Brain 3 product catalog) ---------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/partpilot"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # --- Brain 1: classifier ---------------------------------------------------------------
    CLASSIFIER_INPUT_SIZE: int = 224
    # Below this softmax confidence the orchestrator also searches the
    # runner-up category instead of trusting a single hard gate.
    CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.5
    # Below this confidence, a no-match result states no category at all.
    # When neither model stood behind the image, the winning class is just
    # the least-wrong of ten options, and naming it reads as "we think your
    # living room is a suspension bushing". Mirrors CATEGORY_TRUST_THRESHOLD
    # in frontend/src/components/results/NoCatalogMatchPanel.tsx: the panel
    # and Brain 4 must withhold the same claim, or the page contradicts
    # itself in two places at once.
    CATEGORY_TRUST_THRESHOLD: float = 0.75
    # Pad to a square (white, matching the rembg fill) before resizing,
    # instead of distorting the aspect ratio. Must match how the deployed
    # checkpoint was trained: the current Colab-trained weights saw
    # squashed images, so this stays off until a checkpoint trained with
    # padding replaces them.
    CLASSIFIER_PAD_TO_SQUARE: bool = False

    # --- Brain 2: similarity search ---------------------------------------------------------------
    # Which model turns an image into a vector. One of: openclip, siglip,
    # siglip-large, siglip-so400m, dinov2, dinov2-large, a HuggingFace model id,
    # or several joined with "+" to average their scores (e.g. "dinov2+siglip").
    # Changing this invalidates the FAISS indexes - rebuild after switching.
    # Where the catalog vectors live: "faiss" reads index files from disk,
    # "pgvector" queries the products table. Same vectors and same matches
    # either way - pgvector just keeps them in the product's own row, so they
    # cannot drift out of step with the catalog.
    VECTOR_STORE: str = "faiss"
    EMBEDDING_BACKEND: str = "dinov2"
    # Categories that score better on a different model than the default.
    # Measured with scripts/evaluate_brain2.py: DINOv2 wins overall but loses
    # badly on these, so they keep OpenCLIP. Keyed by catalog category.
    CATEGORY_BACKENDS: dict[str, str] = {
        "Air Filter": "openclip",           # 95.2% vs 66.7% on dinov2
        "Wheel Hub Assembly": "openclip",   # 33.3% vs 16.7%
        "Shock Absorber": "openclip",       # 100% vs 95.8%
    }
    OPENCLIP_MODEL_NAME: str = "ViT-B-32"
    OPENCLIP_PRETRAINED: str = "openai"
    FAISS_TOP_K: int = 10
    # Average the embedding of the image and its mirror at query/build time.
    # Cheap test-time augmentation; both sides must use the same setting, so
    # rebuild indexes after changing it.
    EMBEDDING_TTA: bool = True
    # Below this top similarity the pipeline reports "no catalog match" and
    # skips catalog resolution, instead of confidently naming the nearest
    # wrong part. Scores are cosine against a per-SKU centroid (see
    # FaissIndex.search), keyed per embedding backend because the two models
    # compress cosine space very differently — an out-of-catalog image tops
    # out around 0.83 on dinov2 but 0.92 on openclip, so one global value
    # cannot serve both.
    #
    # Calibrated with scripts/analyze_index_vectors.py over the stored
    # index vectors (rembg + TTA, leave-one-out). Policy: refusing is
    # better than guessing, so these sit at ~1.5% correct-match rejection
    # rather than 0% — the honest trade measured on this catalog:
    #
    #   dinov2   0.45 -> 0.0% rejected / 90.0% impostors caught
    #            0.48 -> 1.3% rejected / 93.1% caught   <- chosen
    #   openclip 0.84 -> 0.0% rejected / 43.9% caught
    #            0.86 -> 1.5% rejected / 62.1% caught   <- chosen
    #
    # (openclip's correct/impostor distributions genuinely overlap more —
    # a known cost of keeping it for the three categories where it ranks
    # far better than dinov2.)
    NO_MATCH_THRESHOLDS: dict[str, float] = {
        "openclip": 0.86,
        "dinov2": 0.48,
    }
    NO_MATCH_THRESHOLD_DEFAULT: float = 0.48
    # Added to the threshold when Brain 1 was itself unsure of the category
    # (confidence below CLASSIFIER_CONFIDENCE_THRESHOLD). Two weak signals
    # — "not sure what kind of part this is" and "nothing especially close
    # in that category" — should not add up to a confident answer.
    NO_MATCH_UNCERTAIN_MARGIN: float = 0.04

    # --- startup ---------------------------------------------------------------
    # Load Brain 1/2 weights and FAISS indexes during startup instead of
    # inside the first request (which otherwise pays a 30-60s cold start).
    WARM_MODELS_ON_STARTUP: bool = True

    # Also preload Brain 4 at boot. Only meaningful with WARM_MODELS_ON_STARTUP.
    # The llama.cpp GGUF loads in seconds, so paying that at startup beats
    # making the first upload wait it out; the transformers path is far
    # heavier, so turn this off if you switch LLM_BACKEND back to it.
    WARM_BRAIN4_ON_STARTUP: bool = True

    # --- Brain 4: reasoning ---------------------------------------------------------------
    HF_TOKEN: str | None = None
    LLM_MODEL_NAME: str = "Qwen/Qwen2.5-1.5B-Instruct"
    LLM_MAX_NEW_TOKENS: int = 256

    # Which Brain 4 implementation to use.
    #
    # "llamacpp" runs a quantised GGUF through llama.cpp; "transformers"
    # runs the full-precision weights through Hugging Face `transformers`.
    # Measured on this catalog's CPU box, transformers took ~23s per
    # explanation, which is unusable in front of a user - llama.cpp runs the
    # same size model several times faster from a smaller file. Both are
    # optional: a failure in either returns the Brain 1-3 answer unchanged.
    LLM_BACKEND: str = "llamacpp"

    # GGUF repo/file for the llama.cpp backend. Q4_K_M is ~1.1 GB - smaller
    # on disk than the 0.5B safetensors while being the stronger model.
    LLM_GGUF_REPO: str = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
    LLM_GGUF_FILE: str = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    #: Context window. The prompt is a short structured summary, so this is
    #: sized for the prompt plus the capped response, not for long chats.
    LLM_CONTEXT_TOKENS: int = 2048
    #: 0 lets llama.cpp pick based on the machine's core count.
    LLM_THREADS: int = 0

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
