"""Tests for the Brain 4 prompt.

The prompt is where the LLM's claims are bounded, so what it is *not* told
matters as much as what it is. In particular the results page withholds the
category on a weak no-match; the prompt has to withhold it too, or the page
asserts and denies the same thing in two panels.
"""

from datetime import UTC, datetime

from backend.pipeline.brain4_reasoning.prompt_builder import PromptBuilder
from backend.schemas.catalog import ProductResponse, VehicleCompatibility
from backend.schemas.prediction import PredictionResponse, SearchResult


def _prediction(*, no_match: bool, confidence: float) -> PredictionResponse:
    return PredictionResponse(
        predicted_category="Oil Filter",
        confidence=confidence,
        search_time_ms=500.0,
        results=[SearchResult(sku="OF-1003", similarity_score=0.39)],
        no_match=no_match,
    )


def test_confident_match_states_the_category() -> None:
    prompt = PromptBuilder().build_explanation_prompt(
        _prediction(no_match=False, confidence=0.94), None, None
    )
    assert "Predicted category: Oil Filter" in prompt
    assert "NOT RECOGNISED" not in prompt


def test_weak_no_match_withholds_the_category() -> None:
    """24% confidence on a no-match: the page says "not recognised", so the
    prompt must not hand Brain 4 a category to repeat."""
    prompt = PromptBuilder().build_explanation_prompt(
        _prediction(no_match=True, confidence=0.24), None, None
    )
    assert "NOT RECOGNISED" in prompt
    assert "Do not name a category" in prompt
    assert "Predicted category: Oil Filter" not in prompt


def test_confident_classifier_on_a_no_match_is_marked_unconfirmed() -> None:
    """The classifier can be sure while the catalog still holds nothing. The
    category is then reportable, but only as unconfirmed."""
    prompt = PromptBuilder().build_explanation_prompt(
        _prediction(no_match=True, confidence=0.88), None, None
    )
    assert "unconfirmed" in prompt
    assert "Oil Filter" in prompt
    assert "NOT RECOGNISED" not in prompt


def test_no_match_prompt_says_no_product_was_resolved() -> None:
    prompt = PromptBuilder().build_explanation_prompt(
        _prediction(no_match=True, confidence=0.24), None, None
    )
    assert "No confident catalog match" in prompt


def _product(vehicles: list[VehicleCompatibility]) -> ProductResponse:
    now = datetime.now(UTC)
    return ProductResponse(
        sku="BP-1002",
        product_name="Duralast Gold Heavy-Duty Front Brake Pad Set",
        brand="Duralast",
        category="Brake Pads",
        compatible_vehicles=vehicles,
        created_at=now,
        updated_at=now,
    )


def test_fitment_is_collapsed_into_year_ranges() -> None:
    """The catalog stores one row per model year. Passed through verbatim the
    model lists every one, which buries the answer and disagrees with the
    range the product page shows beside it."""
    product = _product(
        [VehicleCompatibility(make="Ford", model="F-150", year=y) for y in range(2015, 2021)]
        + [VehicleCompatibility(make="Ford", model="Expedition", year=y) for y in range(2015, 2021)]
    )
    prompt = PromptBuilder().build_explanation_prompt(
        _prediction(no_match=False, confidence=0.94), product, None
    )
    assert "Ford F-150 2015-2020" in prompt
    assert "Ford Expedition 2015-2020" in prompt
    # The per-year repetition is gone.
    assert "F-150 2016" not in prompt
    assert prompt.count("F-150") == 1


def test_a_gap_in_the_years_starts_a_new_range() -> None:
    """A missing year is real fitment data, not noise."""
    product = _product(
        [
            VehicleCompatibility(make="Ford", model="Focus", year=y)
            for y in (2012, 2013, 2014, 2016)
        ]
    )
    prompt = PromptBuilder().build_explanation_prompt(
        _prediction(no_match=False, confidence=0.94), product, None
    )
    assert "Ford Focus 2012-2014" in prompt
    assert "Ford Focus 2016" in prompt
