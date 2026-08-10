"""Guided chat endpoints — the machine asks, the user picks an answer.

A conversation-shaped API over the disambiguation engine
(`backend.pipeline.chat`): `start` opens a session from a prediction's
candidates, `answer` applies one tap (an option, or "Not sure"), `undo`
rewinds the trail, and every response returns the full session state so
the client never reconstructs the conversation from diffs.

The user cannot type into this chat — that is the design, not a gap.
Every option offered is derived from catalog metadata fetched
server-side, so each answer provably narrows real SKUs and nothing can
be invented on either side of the conversation.
"""

from functools import lru_cache

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_product_service
from backend.core.exceptions import CatalogError, ChatStateError, ProductNotFound
from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.product_service import ProductService
from backend.pipeline.chat.engine import (
    Answer,
    ChatCandidate,
    apply_answers,
    collapse_fitment_years,
    detect_visual_mismatch,
    next_question,
    prompt_for,
)
from backend.pipeline.chat.session import ChatSession, ChatSessionStore, ChatTurn
from backend.schemas.catalog import ProductResponse
from backend.schemas.chat import (
    ChatAnswerRecord,
    ChatAnswerRequest,
    ChatMismatchOut,
    ChatOptionOut,
    ChatQuestionOut,
    ChatStartRequest,
    ChatStateResponse,
    ChatUndoRequest,
)
from backend.schemas.response import StandardResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@lru_cache
def get_chat_session_store() -> ChatSessionStore:
    """Process-wide session store, matching the Brain 1/2 singleton pattern."""
    return ChatSessionStore()


def _to_chat_candidate(product: ProductResponse, similarity: float) -> ChatCandidate:
    """Snapshot the catalog facts questions draw on.

    Attribute values are coerced to strings and empty ones dropped, mirroring
    how the frontend treats the attribute bag (truthy string values only).
    """
    attributes = {
        key: str(value)
        for key, value in (product.attributes or {}).items()
        if value is not None and str(value).strip()
    }
    return ChatCandidate(
        sku=product.sku,
        product_name=product.product_name,
        brand=product.brand,
        similarity=similarity,
        manufacturer_part_number=product.manufacturer_part_number,
        attributes=attributes,
        fitment=collapse_fitment_years(
            [(v.make, v.model, v.year) for v in product.compatible_vehicles]
        ),
    )


def _state(session: ChatSession) -> ChatStateResponse:
    """Project a session into the response shape every endpoint returns."""
    remaining = apply_answers(session.candidates, session.answers)
    question = next_question(session.candidates, session.answers, session.skipped)
    session.current_question = question

    mismatch = detect_visual_mismatch(session.candidates, session.answers)
    resolved = remaining[0] if len(remaining) == 1 else None

    if resolved is not None:
        status = "resolved"
    elif question is not None:
        status = "asking"
    else:
        status = "exhausted"

    return ChatStateResponse(
        session_id=session.session_id,
        status=status,
        question=ChatQuestionOut(
            facet=question.facet,
            prompt=question.prompt,
            hint=question.hint,
            options=[ChatOptionOut(label=o.label, skus=list(o.skus)) for o in question.options],
        )
        if question is not None
        else None,
        answers=[
            ChatAnswerRecord(
                facet=turn.facet,
                prompt=turn.prompt,
                label=turn.label,
                # A skip rules nothing out, so every candidate alive at that
                # point stays listed against it.
                skus=list(turn.answer.skus) if turn.answer is not None else [c.sku for c in remaining],
                skipped=turn.skipped,
            )
            for turn in session.turns
        ],
        remaining_skus=[c.sku for c in remaining],
        resolved_sku=resolved.sku if resolved is not None else None,
        mismatch=ChatMismatchOut(
            visual_leader_sku=mismatch.visual_leader.sku,
            visual_leader_similarity=mismatch.visual_leader.similarity,
            best_survivor_sku=mismatch.best_survivor.sku,
            best_survivor_similarity=mismatch.best_survivor.similarity,
        )
        if mismatch is not None
        else None,
    )


@router.post("/start", response_model=StandardResponse[ChatStateResponse])
async def start_chat(
    payload: ChatStartRequest,
    products: ProductService = Depends(get_product_service),
    store: ChatSessionStore = Depends(get_chat_session_store),
) -> StandardResponse[ChatStateResponse]:
    """Open a chat session over a prediction's candidate SKUs.

    Candidates whose SKU is missing from the catalog are skipped with a
    warning rather than failing the conversation — same tolerance the
    recommendation service applies to dangling references.
    """
    candidates: list[ChatCandidate] = []
    for seed in payload.candidates:
        try:
            product = await products.get_product(seed.sku)
        except ProductNotFound:
            logger.warning("Chat start: SKU %s not in catalog; skipping.", seed.sku)
            continue
        candidates.append(_to_chat_candidate(product, seed.similarity))

    if not candidates:
        raise CatalogError("None of the supplied SKUs exist in the catalog.")

    # Best match first — the order both questioning and mismatch detection assume.
    candidates.sort(key=lambda c: c.similarity, reverse=True)
    session = store.create(candidates)
    logger.info(
        "Chat session %s started with %d candidates.", session.session_id, len(candidates)
    )
    return StandardResponse(data=_state(session))


@router.get("/{session_id}", response_model=StandardResponse[ChatStateResponse])
async def get_chat(
    session_id: str,
    store: ChatSessionStore = Depends(get_chat_session_store),
) -> StandardResponse[ChatStateResponse]:
    """Fetch a session's current state (e.g. after a page reload)."""
    return StandardResponse(data=_state(store.get(session_id)))


@router.post("/{session_id}/answer", response_model=StandardResponse[ChatStateResponse])
async def answer_chat(
    session_id: str,
    payload: ChatAnswerRequest,
    store: ChatSessionStore = Depends(get_chat_session_store),
) -> StandardResponse[ChatStateResponse]:
    """Apply one turn: pick an option of the open question, or skip it."""
    session = store.get(session_id)
    question = session.current_question
    if question is None:
        raise ChatStateError("No question is open on this session; nothing to answer.")

    if payload.skip:
        # "Not sure" — never ask this facet again, keep everyone in play. Still
        # recorded as a turn: it is part of the conversation the user had.
        session.turns.append(ChatTurn(facet=question.facet, prompt=question.prompt))
    else:
        if payload.option_index >= len(question.options):  # type: ignore[operator]
            raise ChatStateError(
                f"option_index {payload.option_index} is out of range; "
                f"the open question has {len(question.options)} options."
            )
        option = question.options[payload.option_index]
        session.turns.append(
            ChatTurn(
                facet=question.facet,
                prompt=question.prompt,
                answer=Answer(
                    facet=question.facet,
                    label=option.label,
                    skus=option.skus,
                    row_filter=option.row_filter,
                ),
            )
        )
    return StandardResponse(data=_state(session))


@router.post("/{session_id}/undo", response_model=StandardResponse[ChatStateResponse])
async def undo_chat(
    session_id: str,
    payload: ChatUndoRequest,
    store: ChatSessionStore = Depends(get_chat_session_store),
) -> StandardResponse[ChatStateResponse]:
    """Rewind the transcript to its first `keep` turns.

    A wrong tap early on should stay reversible instead of silently deciding
    the whole result. `keep` counts turns as the client displays them —
    skipped questions included — so "change my second answer" means the same
    thing on both sides.
    """
    session = store.get(session_id)
    if payload.keep > len(session.turns):
        raise ChatStateError(
            f"Cannot keep {payload.keep} turns; the session only has {len(session.turns)}."
        )
    session.turns = session.turns[: payload.keep]
    return StandardResponse(data=_state(session))
