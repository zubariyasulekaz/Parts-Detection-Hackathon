"""Custom exception hierarchy for the backend.

All application-specific exceptions derive from `PartPilotError` so that a
single `except PartPilotError` (or a FastAPI exception handler registered
on that base class) can catch anything the pipeline raises.
"""


class PartPilotError(Exception):
    """Base class for all application errors."""

    #: Machine-readable error code returned in `ErrorResponse.error_code`.
    error_code: str = "PARTPILOT_ERROR"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.__doc__ or self.error_code
        super().__init__(self.message)


class ModelNotLoaded(PartPilotError):
    """Raised when a required model has not been loaded into memory."""

    error_code = "MODEL_NOT_LOADED"


class InvalidImage(PartPilotError):
    """Raised when an uploaded image fails validation or cannot be decoded."""

    error_code = "INVALID_IMAGE"


class CatalogError(PartPilotError):
    """Raised when catalog metadata cannot be read or is inconsistent."""

    error_code = "CATALOG_ERROR"


class ProductNotFound(CatalogError):
    """Raised when a requested product SKU does not exist in the catalog."""

    error_code = "PRODUCT_NOT_FOUND"


class EmbeddingError(PartPilotError):
    """Raised when embedding generation fails."""

    error_code = "EMBEDDING_ERROR"


class SearchError(PartPilotError):
    """Raised when a similarity search against a FAISS index fails."""

    error_code = "SEARCH_ERROR"
