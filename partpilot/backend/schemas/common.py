"""Shared base models and reusable field types.

Nothing in this module should represent a specific API payload — those
belong in `prediction.py`, `catalog.py`, `recommendation.py`, or
`response.py`. This module is for building blocks those files reuse.
"""

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """Base class for all PartPilot API schemas.

    Centralizes Pydantic v2 model configuration so every schema behaves
    consistently (e.g. strips whitespace, forbids unexpected fields).
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        populate_by_name=True,
    )


class Pagination(APIModel):
    """Pagination parameters reusable across list-style endpoints."""

    page: int = 1
    page_size: int = 20
    total_items: int | None = None
