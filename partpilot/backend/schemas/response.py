"""Generic API envelope models.

All endpoints should return either `StandardResponse[T]` on success or
`ErrorResponse` on failure, so API consumers can rely on a single
top-level shape (`success`, plus either `data` or `error_code`/`message`).
"""

from typing import Generic, TypeVar

from backend.schemas.common import APIModel

T = TypeVar("T")


class StandardResponse(APIModel, Generic[T]):
    """Standard success envelope wrapping endpoint-specific payloads."""

    success: bool = True
    message: str = "OK"
    data: T | None = None


class ErrorResponse(APIModel):
    """Standard error envelope returned by exception handlers."""

    success: bool = False
    error_code: str
    message: str
