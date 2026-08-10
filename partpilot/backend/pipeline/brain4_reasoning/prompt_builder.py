"""Prompt construction for Brain 4 (Reasoning).

Builds the user-turn prompt sent to the Brain 4 LLM (Qwen, via
`llm_service.LLMService`). Kept separate from `llm_service.py` so the
prompt format can be iterated on without touching model-loading code.
"""

from backend.config.settings import get_settings
from backend.pipeline.chat.engine import collapse_fitment_years
from backend.schemas.catalog import Product
from backend.schemas.prediction import PredictionResponse
from backend.schemas.recommendation import Recommendation

#: Fixed system prompt: the model's persona and instructions, independent
#: of any single request's data.
SYSTEM_PROMPT = (
    "You are PartPilot, an assistant that helps a mechanic or car owner "
    "confirm they've correctly identified a vehicle part from a photo. "
    "You are given the output of an image classifier and a visual "
    "similarity search against a parts catalog. Write a short (2-4 "
    "sentence) explanation of the match, then ask up to 3 short, "
    "specific clarifying questions ONLY if something is genuinely "
    "ambiguous (e.g. several compatible vehicles, low confidence, or "
    "multiple close-scoring alternatives). If the match is clear and "
    "unambiguous, say so plainly and skip the questions. Keep the whole "
    "response under 150 words.\n\n"
    "State only what the data below says. Never assert a category or a part "
    "the data marks as not recognised or unmatched, never describe a part's "
    "condition, and never call two different SKUs the same product - they are "
    "different parts from different manufacturers."
)


class PromptBuilder:
    """Builds LLM prompts from pipeline results."""

    def _fitment(self, product: Product) -> str:
        """Fitment as year ranges, the way the product page renders it.

        The catalog stores one row per model year, so a part fitting an F-150
        from 2015 to 2020 arrives as six rows. Passed through verbatim the
        model dutifully lists every one - "Ford F-150 2015, Ford F-150 2016,
        …" - which buries the answer, spends generation time on repetition,
        and disagrees with the "Ford F-150 (2015-2020)" the page shows beside
        it. A gap in the years still starts a new range: that gap is real
        fitment data, not noise.
        """
        ranges = collapse_fitment_years(
            [(v.make, v.model, v.year) for v in product.compatible_vehicles]
        )
        return ", ".join(
            f"{r.make} {r.model} "
            + (str(r.year_start) if r.year_start == r.year_end else f"{r.year_start}-{r.year_end}")
            for r in ranges
        )

    def _category_line(self, prediction: PredictionResponse) -> str:
        """State the category only as strongly as the evidence allows.

        On a no-match with a weak classifier, the winning class is the
        least-wrong of ten options rather than a finding, and the results page
        says so ("not recognised"). Handing Brain 4 a bare "Predicted
        category: Oil Filter" invites it to repeat that as fact underneath a
        panel refusing to make the same claim - the page then contradicts
        itself, which is worse than saying nothing.
        """
        confidence = f"{prediction.confidence:.0%}"
        if not prediction.no_match:
            return f"Predicted category: {prediction.predicted_category} (confidence: {confidence})"
        if prediction.confidence >= get_settings().CATEGORY_TRUST_THRESHOLD:
            return (
                f"Category (unconfirmed - nothing in the catalog matched): "
                f"{prediction.predicted_category} at {confidence} confidence"
            )
        return (
            f"Category: NOT RECOGNISED. The classifier's best guess reached only "
            f"{confidence} confidence, which is too low to state. Do not name a "
            f"category in your reply."
        )

    def build_explanation_prompt(
        self,
        prediction: PredictionResponse,
        product: Product | None,
        recommendation: Recommendation | None,
    ) -> str:
        """Construct the user-turn prompt describing the pipeline result."""
        lines = [self._category_line(prediction), "Top matched SKUs (by visual similarity):"]
        for result in prediction.results[:5]:
            lines.append(f"  - {result.sku} (similarity: {result.similarity_score:.0%})")

        if product is not None:
            lines.append("")
            lines.append(
                f"Matched catalog product: {product.sku} — "
                f"{product.product_name} ({product.brand})"
            )
            if product.compatible_vehicles:
                lines.append(f"Compatible vehicles: {self._fitment(product)}")
            else:
                lines.append("Compatible vehicles: not specified in the catalog.")
        else:
            lines.append("")
            lines.append("No confident catalog match was found for the top SKU.")

        if recommendation is not None:
            if recommendation.alternatives:
                alt_skus = ", ".join(p.sku for p in recommendation.alternatives)
                lines.append(f"Alternative/replacement SKUs: {alt_skus}")
            if recommendation.accessories:
                acc_skus = ", ".join(p.sku for p in recommendation.accessories)
                lines.append(f"Related accessory SKUs: {acc_skus}")

        return "\n".join(lines)
