"""Part identification prediction endpoint.

Endpoint logic is intentionally NOT implemented — see module-level TODO.
Returns a dummy `PredictionResponse` so the API contract is testable end
-to-end before the AI pipeline exists.
"""

from fastapi import APIRouter, Depends, File, UploadFile

from backend.api.dependencies import get_orchestrator
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.schemas.prediction import PredictionResponse, SearchResult
from backend.schemas.response import StandardResponse

router = APIRouter(prefix="/predict", tags=["Prediction"])


@router.post("", response_model=StandardResponse[PredictionResponse])
async def predict_part(
    file: UploadFile = File(...),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> StandardResponse[PredictionResponse]:
    """Identify a vehicle part from an uploaded image.

    TODO: Replace the dummy response below with a real call once Brain
    1-3 are implemented, e.g.:
        image = load_image_from_bytes(await file.read())
        result = orchestrator.run(image)
        return StandardResponse(data=result.prediction)

    Args:
        file: The uploaded part image (multipart/form-data).
        orchestrator: Injected pipeline orchestrator (unused until the
            AI pipeline is implemented).
    """
    dummy_response = PredictionResponse(
        predicted_category="oil_filter",
        confidence=0.0,
        search_time_ms=0.0,
        results=[SearchResult(sku="PLACEHOLDER-SKU-001", similarity_score=0.0)],
    )
    return StandardResponse(message="Dummy prediction (pipeline not yet implemented)", data=dummy_response)
