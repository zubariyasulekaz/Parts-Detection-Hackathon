"""Prompt construction for Brain 4 (Reasoning).

Builds the user-turn prompt sent to the Brain 4 LLM (Qwen, via
`llm_service.LLMService`). Kept separate from `llm_service.py` so the
prompt format can be iterated on without touching model-loading code.
"""

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
    "response under 150 words."
)


class PromptBuilder:
    """Builds LLM prompts from pipeline results."""

    def build_explanation_prompt(
        self,
        prediction: PredictionResponse,
        product: Product | None,
        recommendation: Recommendation | None,
    ) -> str:
        """Construct the user-turn prompt describing the pipeline result."""
        lines = [
            f"Predicted category: {prediction.predicted_category} "
            f"(confidence: {prediction.confidence:.0%})",
            "Top matched SKUs (by visual similarity):",
        ]
        for result in prediction.results[:5]:
            lines.append(f"  - {result.sku} (similarity: {result.similarity_score:.0%})")

        if product is not None:
            lines.append("")
            lines.append(
                f"Matched catalog product: {product.sku} — "
                f"{product.product_name} ({product.brand})"
            )
            if product.compatible_vehicles:
                vehicles = ", ".join(
                    f"{v.make} {v.model} {v.year}" for v in product.compatible_vehicles
                )
                lines.append(f"Compatible vehicles: {vehicles}")
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
