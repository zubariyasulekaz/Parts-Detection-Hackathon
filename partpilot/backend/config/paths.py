"""Centralized filesystem path definitions for the PartPilot backend.

All other modules should import paths from here rather than constructing
their own relative paths, so the on-disk layout only needs to change in
one place.
"""

from pathlib import Path

# backend/config/paths.py -> backend/
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent

# repository root (parent of backend/)
ROOT_DIR: Path = BACKEND_DIR.parent

# --- data ---------------------------------------------------------------
DATA_DIR: Path = BACKEND_DIR / "data"
CATALOG_DATA_DIR: Path = DATA_DIR / "catalog"
EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
INDEXES_DIR: Path = DATA_DIR / "indexes"
UPLOADS_DIR: Path = DATA_DIR / "uploads"

# --- models ---------------------------------------------------------------
MODELS_DIR: Path = BACKEND_DIR / "models"
CLASSIFIER_MODEL_DIR: Path = MODELS_DIR / "classifier"
CLIP_MODEL_DIR: Path = MODELS_DIR / "clip"
FAISS_MODEL_DIR: Path = MODELS_DIR / "faiss"

# --- other top level dirs ---------------------------------------------------------------
DATASETS_DIR: Path = ROOT_DIR / "datasets"
CATALOG_CSV_PATH: Path = DATASETS_DIR / "catalog.csv"
NOTEBOOKS_DIR: Path = ROOT_DIR / "notebooks"
SCRIPTS_DIR: Path = ROOT_DIR / "scripts"
DOCS_DIR: Path = ROOT_DIR / "docs"

ALL_RUNTIME_DIRS: tuple[Path, ...] = (
    CATALOG_DATA_DIR,
    EMBEDDINGS_DIR,
    INDEXES_DIR,
    UPLOADS_DIR,
    CLASSIFIER_MODEL_DIR,
    CLIP_MODEL_DIR,
    FAISS_MODEL_DIR,
)


def ensure_runtime_directories() -> None:
    """Create all runtime data/model directories if they do not exist.

    Safe to call multiple times (idempotent). Intended to be invoked once
    during application startup.
    """
    for directory in ALL_RUNTIME_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
