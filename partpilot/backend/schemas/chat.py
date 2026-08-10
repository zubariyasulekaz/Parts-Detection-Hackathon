"""Schemas for the guided chat endpoints (`/chat/*`).

The conversation contract: the machine asks, the user picks. Every
response returns the full session state (`ChatStateResponse`), so the
client renders from one shape whether it just started, answered, or
undid — there is no incremental diff to reconcile.
"""

from typing import Literal

from pydantic import Field, model_validator

from backend.schemas.common import APIModel


class ChatSeedCandidate(APIModel):
    """One candidate from the prediction the chat narrows down.

    Only the SKU and its similarity score come from the client — every
    fact questions are built from (fitment, brand, attributes) is fetched
    server-side from the catalog, so the conversation cannot be fed
    invented product data.
    """

    sku: str = Field(min_length=1)
    similarity: float = Field(ge=-1.0, le=1.0)


class ChatStartRequest(APIModel):
    """Payload for `POST /chat/start`."""

    candidates: list[ChatSeedCandidate] = Field(min_length=1, max_length=25)


class ChatOptionOut(APIModel):
    """One tappable answer. `skus` lets the client show how many candidates
    survive each choice (and dim ruled-out cards in step)."""

    label: str
    skus: list[str]


class ChatQuestionOut(APIModel):
    """The question currently on the table."""

    facet: str
    prompt: str
    hint: str
    options: list[ChatOptionOut]


class ChatAnswerRecord(APIModel):
    """One completed turn — the question, what the user did, and its effect.

    Skips are turns too: `skipped=true` with the label "Not sure" and every
    candidate still in `skus`, so the client can render the exchange in the
    order it happened rather than silently dropping it.

    `skus` (the candidates that choice kept) lets the client re-derive
    anything the trail implies without a further round trip."""

    facet: str
    prompt: str
    label: str
    skus: list[str]
    skipped: bool = False


class ChatMismatchOut(APIModel):
    """The user's answers ruled out the candidate the photo most strongly
    favoured — surfaced so the client can offer the choice instead of
    silently letting one signal overrule the other."""

    visual_leader_sku: str
    visual_leader_similarity: float
    best_survivor_sku: str
    best_survivor_similarity: float


class ChatStateResponse(APIModel):
    """The whole conversation, as the server sees it."""

    session_id: str
    #: `asking` — a question is open. `resolved` — one candidate left.
    #: `exhausted` — several left and nothing further separates them; the
    #: client should fall back to manual choice among `remaining_skus`.
    status: Literal["asking", "resolved", "exhausted"]
    question: ChatQuestionOut | None = None
    #: The full transcript in order — answered turns and skipped ones.
    answers: list[ChatAnswerRecord] = Field(default_factory=list)
    #: Ranked best-first; the client dims cards not in this list.
    remaining_skus: list[str] = Field(default_factory=list)
    resolved_sku: str | None = None
    mismatch: ChatMismatchOut | None = None


class ChatAnswerRequest(APIModel):
    """Payload for `POST /chat/{session_id}/answer`.

    Exactly one of `option_index` (pick that option of the current
    question) or `skip` (answer "Not sure" — the facet is never asked
    again) must be provided.
    """

    option_index: int | None = Field(default=None, ge=0)
    skip: bool = False

    @model_validator(mode="after")
    def _exactly_one_action(self) -> "ChatAnswerRequest":
        if (self.option_index is None) == (not self.skip):
            raise ValueError("Provide exactly one of option_index or skip=true.")
        return self


class ChatUndoRequest(APIModel):
    """Payload for `POST /chat/{session_id}/undo`.

    Rewinds the answer trail to its first `keep` entries. `keep=0` with
    default flags is a full restart (skipped facets are cleared too, so
    every question becomes askable again).
    """

    keep: int = Field(ge=0)
