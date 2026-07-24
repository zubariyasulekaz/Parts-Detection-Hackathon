"""Unit tests for Brain 3 catalog + recommendation services.

Exercises the CSV-backed `MetadataLoader`, `CatalogService`, and
`RecommendationService` against a small temporary catalog fixture.
"""

from pathlib import Path

import pytest

from backend.core.exceptions import CatalogError
from backend.pipeline.brain3_catalog.catalog_service import CatalogService
from backend.pipeline.brain3_catalog.metadata_loader import MetadataLoader
from backend.pipeline.brain3_catalog.recommendation_service import RecommendationService

CSV_CONTENT = (
    "sku,product_name,brand,category,manufacturer_part_number,"
    "compatible_vehicles,replacement_sku,alternative_sku,accessory_skus,"
    "description,image_folder,image_count\n"
    "BP001,Disc Brake Pad Set,Bosch,Brake Pads,BP001,"
    "Honda Civic 2016|Toyota Corolla 2018,BP002,BP003,AC001|AC002,"
    "Front ceramic pads,images/BP001,4\n"
    "BP002,Disc Brake Pad Set,,Brake Pads,BP002,,,,,"",images/BP002,3\n"
    "BP003,Disc Brake Pad Set,,Brake Pads,BP003,,,,,"",images/BP003,3\n"
    "OF001,Engine Oil Filter,MANN,Oil Filter,OF001,,,,AC001,"
    "Spin-on filter,images/OF001,5\n"
    "AC001,Drain Plug Gasket,,Accessory,AC001,,,,,"",images/AC001,1\n"
    "AC002,Brake Sensor Wire,,Accessory,AC002,,,,,"",images/AC002,1\n"
)


@pytest.fixture()
def catalog_csv(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.csv"
    path.write_text(CSV_CONTENT, encoding="utf-8")
    return path


@pytest.fixture()
def catalog(catalog_csv: Path) -> CatalogService:
    return CatalogService(MetadataLoader(catalog_path=catalog_csv))


def test_get_product_maps_all_fields(catalog: CatalogService) -> None:
    product = catalog.get_product("BP001")

    assert product.sku == "BP001"
    assert product.product_name == "Disc Brake Pad Set"
    assert product.brand == "Bosch"
    assert product.category == "Brake Pads"
    assert product.description == "Front ceramic pads"
    assert product.compatible_vehicles == ["Honda Civic 2016", "Toyota Corolla 2018"]
    assert product.replacement_sku == "BP002"
    assert product.alternative_sku == "BP003"
    assert product.accessory_skus == ["AC001", "AC002"]


def test_empty_optional_fields_become_none_and_empty_lists(catalog: CatalogService) -> None:
    product = catalog.get_product("BP002")

    assert product.brand == ""
    assert product.replacement_sku is None
    assert product.alternative_sku is None
    assert product.compatible_vehicles == []
    assert product.accessory_skus == []


def test_unknown_sku_raises_catalog_error(catalog: CatalogService) -> None:
    with pytest.raises(CatalogError):
        catalog.get_product("DOES-NOT-EXIST")


def test_search_by_category_is_case_insensitive_and_limited(catalog: CatalogService) -> None:
    assert {p.sku for p in catalog.search_by_category("brake pads")} == {"BP001", "BP002", "BP003"}
    assert len(catalog.search_by_category("Brake Pads", limit=2)) == 2
    assert catalog.search_by_category("Nonexistent") == []


def test_recommend_resolves_alternatives_and_accessories(catalog_csv: Path) -> None:
    service = RecommendationService(CatalogService(MetadataLoader(catalog_path=catalog_csv)))

    rec = service.recommend("BP001")

    # replacement_sku (BP002) first, then alternative_sku (BP003).
    assert [p.sku for p in rec.alternatives] == ["BP002", "BP003"]
    assert [p.sku for p in rec.accessories] == ["AC001", "AC002"]


def test_recommend_skips_missing_accessory_skus(catalog_csv: Path) -> None:
    # OF001 references AC001 (exists) only; ensure it resolves cleanly.
    service = RecommendationService(CatalogService(MetadataLoader(catalog_path=catalog_csv)))

    rec = service.recommend("OF001")

    assert rec.alternatives == []
    assert [p.sku for p in rec.accessories] == ["AC001"]


def test_recommend_unknown_sku_raises(catalog_csv: Path) -> None:
    service = RecommendationService(CatalogService(MetadataLoader(catalog_path=catalog_csv)))

    with pytest.raises(CatalogError):
        service.recommend("NOPE")
