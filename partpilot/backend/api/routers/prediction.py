"""Part identification prediction endpoint.

Runs the full pipeline: upload -> background removal -> EfficientNet
classification -> per-category similarity search -> catalog lookup +
recommendations -> LLM explanation/clarifying questions.

Each finished run is also recorded to the audit trail, which is what
`backend.api.routers.history` reads back.
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile

from backend.api.dependencies import (
    get_app_settings,
    get_orchestrator,
    get_prediction_audit_service,
)
from backend.config.settings import Settings
from backend.core.exceptions import InvalidImage, PartPilotError, PredictionError
from backend.core.logging import get_logger
from backend.pipeline.audit.service import PredictionAuditService
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.schemas.audit import (
    AuditCandidate,
    AuditEntryCreate,
    AuditEntryResponse,
    PredictionConfirmRequest,
)
from backend.schemas.prediction import PredictionResult
from backend.schemas.response import StandardResponse
from backend.utils.image_utils import encode_thumbnail_data_url, load_image_from_bytes

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
    audit_service: PredictionAuditService = Depends(get_prediction_audit_service),
    settings: Settings = Depends(get_app_settings),
) -> StandardResponse[PredictionResult]:
    """Identify a vehicle part from an uploaded image.

    Args:
        file: The uploaded part image (multipart/form-data).
        top_k: How many similar SKUs to return.
        explain: Whether to invoke Brain 4 for a natural-language
            explanation and clarifying questions.
        orchestrator: Injected pipeline orchestrator.
        audit_service: Injected audit trail service; records the run.
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
    except (ConnectionError, OSError, TimeoutError) as exc:
        # Distinguished from the catch-all below because this one is
        # actionable: it's Brain 3 (the Postgres catalog) being
        # unreachable, not a pipeline bug. Most often the IPv6-only
        # Supabase direct-connection host on a network without IPv6 -
        # see check_database() in backend.core.startup, which flags this
        # at boot, and docs/RUNNING.md for the session-pooler fix.
        raise PredictionError(
            "Cannot reach the product catalog database right now. If this is "
            "unexpected, check DATABASE_URL in .env and see docs/RUNNING.md "
            "(look for the IPv6/session-pooler note)."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise PredictionError(f"Prediction pipeline failed: {exc}") from exc

    no_match = result.prediction.no_match
    top = result.prediction.results[0].sku if result.prediction.results else None

    # The audit trail is a by-product of answering, never a precondition for
    # it, so every step of recording — thumbnailing the upload, building the
    # row, writing it — degrades the same way Brain 4 does in
    # `PipelineOrchestrator.run`: log what was lost and hand back the result
    # the pipeline already produced. `PredictionAuditService.record` swallows
    # (and rolls back) write failures on its own; this guard covers the rest.
    audit_id: int | None = None
    try:
        # `image` is still the decoded upload: `orchestrator.run` rebinds the
        # background-stripped copy to its own local and never touches ours.
        recorded = await audit_service.record(
            AuditEntryCreate(
                predicted_category=result.prediction.predicted_category,
                confidence=result.prediction.confidence,
                search_time_ms=result.prediction.search_time_ms,
                # A below-threshold nearest neighbour is context, not an
                # answer — the trail must not record it as one.
                top_sku=None if no_match else top,
                candidates=[
                    AuditCandidate(sku=r.sku, similarity_score=r.similarity_score, rank=rank)
                    for rank, r in enumerate(result.prediction.results, start=1)
                ],
                # The backend that actually embedded the query, as reported
                # by Brain 2 (follows the index, not the configured default).
                embedding_backend=result.prediction.embedding_backend,
                explanation=result.explanation,
                thumbnail=encode_thumbnail_data_url(image),
            )
        )
        audit_id = recorded.id if recorded else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Prediction not recorded; returning the result anyway: %s", exc)

    return StandardResponse(
        message="No catalog match" if no_match or not top else f"Best match: {top}",
        data=PredictionResult(
            prediction=result.prediction,
            product=result.product,
            recommendation=result.recommendation,
            explanation=result.explanation,
            audit_id=audit_id,
        ),
    )


@router.post("/{audit_id}/confirm", response_model=StandardResponse[AuditEntryResponse])
async def confirm_prediction(
    audit_id: int,
    payload: PredictionConfirmRequest,
    audit_service: PredictionAuditService = Depends(get_prediction_audit_service),
) -> StandardResponse[AuditEntryResponse]:
    """Record which SKU the user settled on for a recorded prediction.

    Closes the feedback loop the audit trail exists for: a confirmation
    matching the pipeline's `top_sku` validates the run, one differing
    from it labels the run as a correction — training data the catalog
    earns just by being used.

    Args:
        audit_id: The `audit_id` returned by `POST /predict`.
        payload: The confirmed SKU plus any guided-question answers that
            led to it.
        audit_service: Injected audit trail service.

    Returns:
        The updated audit entry.
    """
    entry = await audit_service.confirm(
        audit_id, payload.confirmed_sku, payload.disambiguation
    )
    return StandardResponse(
        message=f"Recorded confirmation of {payload.confirmed_sku}",
        data=entry,
    )
