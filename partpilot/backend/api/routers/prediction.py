"""Part identification prediction endpoint.

Runs the full pipeline: upload -> background removal -> EfficientNet
classification -> per-category similarity search -> catalog lookup +
recommendations -> LLM explanation/clarifying questions.
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile

from backend.api.dependencies import get_app_settings, get_orchestrator
from backend.config.settings import Settings
from backend.core.exceptions import InvalidImage, PartPilotError, PredictionError
from backend.core.logging import get_logger
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.schemas.prediction import PredictionResult
from backend.schemas.response import StandardResponse
from backend.utils.image_utils import load_image_from_bytes

logger = get_logger(__name__)

router = APIRouter(prefix="/predict", tags=["Prediction"])


@router.post("", response_model=StandardResponse[PredictionResult])
async def predict_part(
    file: UploadFile = File(...),
    top_k: int = Query(default=5, ge=1, le=50, description="Number of matches to return."),
    explain: bool = Query(
        default=True,
        description="Whether to run Brain 4 (Qwen) for an explanation + clarifying questions.",
    ),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_app_settings),
) -> StandardResponse[PredictionResult]:
    """Identify a vehicle part from an uploaded image.

    Args:
        file: The uploaded part image (multipart/form-data).
        top_k: How many similar SKUs to return.
        explain: Whether to invoke Brain 4 for a natural-language
            explanation and clarifying questions.
        orchestrator: Injected pipeline orchestrator.
        settings: Injected application settings (upload limits).

    Returns:
        A `PredictionResult` with the predicted category + top-K matches,
        the resolved catalog product, alternative/accessory
        recommendations, and (if `explain`) an LLM-generated explanation.
    """
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise InvalidImage(
            f"Uploaded image exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
        )

    image = load_image_from_bytes(content)

    try:
        result = await orchestrator.run(image, top_k=top_k, explain=explain)
    except PartPilotError:
        raise  # domain errors -> mapped to HTTP status by the global handler
    except Exception as exc:  # noqa: BLE001
        raise PredictionError(f"Prediction pipeline failed: {exc}") from exc

    top = result.prediction.results[0].sku if result.prediction.results else None
    return StandardResponse(
        message=f"Best match: {top}" if top else "No match found",
        data=PredictionResult(
            prediction=result.prediction,
            product=result.product,
            recommendation=result.recommendation,
            explanation=result.explanation,
        ),
    )
