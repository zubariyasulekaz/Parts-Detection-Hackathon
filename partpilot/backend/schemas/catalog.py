"""Schemas describing catalog entries (Brain 3 persistence layer).

`ProductCreate`/`ProductUpdate` are the write-side payloads accepted by
the `/products` endpoints; `ProductResponse` is what gets serialized
back out, including DB-generated fields (`created_at`, `updated_at`).
All three build on `ProductBase` so field definitions (and validation)
live in exactly one place.
"""

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from backend.schemas.common import APIModel


class VehicleCompatibility(APIModel):
    """A single vehicle make/model/year a product is compatible with."""

    make: str = Field(min_length=1)
    model: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)


class ProductBase(APIModel):
    """Fields shared by every product create/update/response payload."""

    product_name: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description: str | None = None
    #: The number stamped on the part / printed on the box, e.g. "DE1439".
    manufacturer_part_number: str | None = None
    #: Visual facts that separate look-alike SKUs (filter_style, position,
    #: primary_colour, …). Keys vary by category, so this is deliberately open.
    attributes: dict[str, Any] = Field(default_factory=dict)
    image_paths: list[str] = Field(default_factory=list)
    replacement_sku: str | None = None
    alternative_skus: list[str] = Field(default_factory=list)
    accessory_skus: list[str] = Field(default_factory=list)
    compatible_vehicles: list[VehicleCompatibility] = Field(default_factory=list)


class ProductCreate(ProductBase):
    """Payload for `POST /products`."""

    sku: str = Field(min_length=1)


class ProductUpdate(APIModel):
    """Payload for `PUT /products/{sku}`.

    Every field is optional: only fields explicitly present in the
    request body are applied (see `ProductRepository.update`, which
    uses `model_dump(exclude_unset=True)`). `sku` is the immutable
    primary key and is not updatable.
    """

    product_name: str | None = Field(default=None, min_length=1)
    brand: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1)
    description: str | None = None
    image_paths: list[str] | None = None
    replacement_sku: str | None = None
    alternative_skus: list[str] | None = None
    accessory_skus: list[str] | None = None
    compatible_vehicles: list[VehicleCompatibility] | None = None


class ProductResponse(ProductBase):
    """Full catalog product record, as returned by the API.

    `from_attributes=True` lets this be built directly from a
    `backend.pipeline.brain3_catalog.models.Product` ORM instance via
    `ProductResponse.model_validate(orm_instance)`.
    """

    model_config = ConfigDict(from_attributes=True)

    sku: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime


# Backward-compatible alias: the classifier/similarity-search/reasoning
# interfaces and `Recommendation` refer to the catalog output type as
# `Product`.
Product = ProductResponse
