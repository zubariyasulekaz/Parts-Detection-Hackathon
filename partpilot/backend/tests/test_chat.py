"""Tests for the guided chat: the engine's question logic and the
`/chat/*` endpoints.

The engine tests exercise the pure logic directly. The endpoint tests go
through the API with a fake `ProductService` (same `dependency_overrides`
approach as `test_catalog.py`), so no live Postgres is required.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_product_service
from backend.api.routers.chat import get_chat_session_store
from backend.app import create_app
from backend.core.exceptions import ProductNotFound
from backend.pipeline.chat.engine import (
    Answer,
    ChatCandidate,
    FitmentRange,
    apply_answers,
    collapse_fitment_years,
    detect_visual_mismatch,
    next_question,
)
from backend.pipeline.chat.session import ChatSessionStore
from backend.schemas.catalog import ProductResponse, VehicleCompatibility


def _candidate(
    sku: str,
    similarity: float,
    brand: str = "Bosch",
    mpn: str | None = None,
    attributes: dict[str, str] | None = None,
    fitment: tuple[FitmentRange, ...] = (),
) -> ChatCandidate:
    return ChatCandidate(
        sku=sku,
        product_name=f"Part {sku}",
        brand=brand,
        similarity=similarity,
        manufacturer_part_number=mpn,
        attributes=attributes or {},
        fitment=fitment,
    )


# ---------------------------------------------------------------- engine


def test_attribute_question_preferred_over_vehicle() -> None:
    """Visual attributes are asked first: they need no knowledge at all."""
    candidates = [
        _candidate(
            "A",
            0.9,
            attributes={"filter_style": "spin-on"},
            fitment=(FitmentRange("Honda", "Civic", 2018, 2022),),
        ),
        _candidate(
            "B",
            0.88,
            attributes={"filter_style": "cartridge"},
            fitment=(FitmentRange("Toyota", "Camry", 2018, 2022),),
        ),
    ]
    question = next_question(candidates, [], [])
    assert question is not None
    assert question.facet == "attr:filter_style"
    labels = {option.label for option in question.options}
    assert labels == {"Spin-on", "Cartridge"}


def test_attribute_skipped_when_a_candidate_lacks_it() -> None:
    """A missing attribute is a data gap, not a mismatch — never a question."""
    candidates = [
        _candidate(
            "A",
            0.9,
            attributes={"filter_style": "spin-on"},
            fitment=(FitmentRange("Honda", "Civic", 2018, 2022),),
        ),
        _candidate("B", 0.88, fitment=(FitmentRange("Toyota", "Camry", 2018, 2022),)),
    ]
    question = next_question(candidates, [], [])
    assert question is not None
    assert question.facet == "make"


def test_answers_narrow_to_resolution() -> None:
    candidates = [
        _candidate("A", 0.9, fitment=(FitmentRange("Honda", "Civic", 2018, 2022),)),
        _candidate("B", 0.88, fitment=(FitmentRange("Toyota", "Camry", 2018, 2022),)),
    ]
    question = next_question(candidates, [], [])
    assert question is not None and question.facet == "make"
    honda = next(option for option in question.options if option.label == "Honda")
    answers = [Answer("make", honda.label, honda.skus, honda.row_filter)]
    remaining = apply_answers(candidates, answers)
    assert [c.sku for c in remaining] == ["A"]
    assert next_question(candidates, answers, []) is None


def test_skipped_facet_is_not_asked_again() -> None:
    candidates = [
        _candidate("A", 0.9, brand="Bosch", fitment=(FitmentRange("Honda", "Civic", 2018, 2022),)),
        _candidate("B", 0.88, brand="Akebono", fitment=(FitmentRange("Toyota", "Camry", 2018, 2022),)),
    ]
    question = next_question(candidates, [], ["make", "model"])
    assert question is not None
    assert question.facet not in {"make", "model"}


def test_no_vehicle_question_when_fitment_is_incomplete() -> None:
    """No fitment on one candidate: "no rows" must not read as "does not fit"."""
    candidates = [
        _candidate("A", 0.9, brand="Bosch", fitment=(FitmentRange("Honda", "Civic", 2018, 2022),)),
        _candidate("B", 0.88, brand="Akebono"),
    ]
    question = next_question(candidates, [], [])
    assert question is not None
    assert question.facet == "brand"


def test_year_ranges_collapse_runs_and_keep_gaps() -> None:
    rows = [
        ("Ford", "Focus", 2012),
        ("Ford", "Focus", 2013),
        ("Ford", "Focus", 2014),
        # 2015 missing — the gap is real fitment data and must survive.
        ("Ford", "Focus", 2016),
    ]
    ranges = collapse_fitment_years(rows)
    assert ranges == (
        FitmentRange("Ford", "Focus", 2012, 2014),
        FitmentRange("Ford", "Focus", 2016, 2016),
    )


def test_mismatch_fires_only_when_photo_had_a_decisive_favourite() -> None:
    decisive = [
        _candidate("A", 0.95, fitment=(FitmentRange("Honda", "Civic", 2018, 2022),)),
        _candidate("B", 0.80, fitment=(FitmentRange("Toyota", "Camry", 2018, 2022),)),
    ]
    close = [
        _candidate("A", 0.86, fitment=(FitmentRange("Honda", "Civic", 2018, 2022),)),
        _candidate("B", 0.85, fitment=(FitmentRange("Toyota", "Camry", 2018, 2022),)),
    ]
    ruled_out_leader = [Answer("make", "Toyota", ("B",), None)]

    mismatch = detect_visual_mismatch(decisive, ruled_out_leader)
    assert mismatch is not None
    assert mismatch.visual_leader.sku == "A"
    assert mismatch.best_survivor.sku == "B"
    # Close scores are exactly why the chat exists — no warning there.
    assert detect_visual_mismatch(close, ruled_out_leader) is None


# ------------------------------------------------------------- endpoints


class FakeProductService:
    """Read-only stand-in serving a fixed three-candidate catalog."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self._products = {
            product.sku: product
            for product in [
                ProductResponse(
                    sku="BP-HONDA",
                    product_name="Front Brake Pads (Honda)",
                    brand="Bosch",
                    category="Brake Pads",
                    attributes={"wear_sensor": "yes"},
                    compatible_vehicles=[
                        VehicleCompatibility(make="Honda", model="Civic", year=year)
                        for year in range(2018, 2023)
                    ],
                    created_at=now,
                    updated_at=now,
                ),
                ProductResponse(
                    sku="BP-TOYOTA",
                    product_name="Front Brake Pads (Toyota)",
                    brand="Akebono",
                    category="Brake Pads",
                    attributes={"wear_sensor": "no"},
                    compatible_vehicles=[
                        VehicleCompatibility(make="Toyota", model="Camry", year=year)
                        for year in range(2018, 2023)
                    ],
                    created_at=now,
                    updated_at=now,
                ),
                ProductResponse(
                    sku="BP-BMW",
                    product_name="Front Brake Pads (BMW)",
                    brand="Bosch",
                    category="Brake Pads",
                    attributes={"wear_sensor": "yes"},
                    compatible_vehicles=[
                        VehicleCompatibility(make="BMW", model="3 Series", year=year)
                        for year in range(2019, 2024)
                    ],
                    created_at=now,
                    updated_at=now,
                ),
            ]
        }

    async def get_product(self, sku: str) -> ProductResponse:
        product = self._products.get(sku)
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        return product


@pytest.fixture
def chat_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_product_service] = FakeProductService
    # A fresh store per test — the module-level one is a process singleton.
    store = ChatSessionStore()
    app.dependency_overrides[get_chat_session_store] = lambda: store
    return TestClient(app)


SEED = {
    "candidates": [
        {"sku": "BP-HONDA", "similarity": 0.91},
        {"sku": "BP-TOYOTA", "similarity": 0.89},
        {"sku": "BP-BMW", "similarity": 0.87},
    ]
}


def test_start_opens_an_asking_session(chat_client: TestClient) -> None:
    response = chat_client.post("/api/v1/chat/start", json=SEED)
    assert response.status_code == 200
    state = response.json()["data"]
    assert state["status"] == "asking"
    assert state["question"] is not None
    assert state["remaining_skus"] == ["BP-HONDA", "BP-TOYOTA", "BP-BMW"]
    assert state["resolved_sku"] is None


def test_unknown_skus_are_skipped_not_fatal(chat_client: TestClient) -> None:
    seed = {
        "candidates": [
            {"sku": "BP-HONDA", "similarity": 0.91},
            {"sku": "GHOST-1", "similarity": 0.90},
            {"sku": "BP-TOYOTA", "similarity": 0.89},
        ]
    }
    response = chat_client.post("/api/v1/chat/start", json=seed)
    assert response.status_code == 200
    assert response.json()["data"]["remaining_skus"] == ["BP-HONDA", "BP-TOYOTA"]


def test_start_with_no_known_skus_is_an_error(chat_client: TestClient) -> None:
    response = chat_client.post(
        "/api/v1/chat/start", json={"candidates": [{"sku": "GHOST-1", "similarity": 0.9}]}
    )
    assert response.status_code == 404


def test_answering_narrows_and_resolves(chat_client: TestClient) -> None:
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    session_id = state["session_id"]

    # Answer questions until the session resolves; the engine guarantees
    # progress because every offered option keeps at least one SKU.
    for _ in range(10):
        if state["status"] != "asking":
            break
        options = state["question"]["options"]
        # Always take the option keeping the fewest SKUs — fastest narrowing.
        index = min(range(len(options)), key=lambda i: len(options[i]["skus"]))
        response = chat_client.post(
            f"/api/v1/chat/{session_id}/answer", json={"option_index": index}
        )
        assert response.status_code == 200
        state = response.json()["data"]

    assert state["status"] == "resolved"
    assert state["resolved_sku"] in {"BP-HONDA", "BP-TOYOTA", "BP-BMW"}
    assert len(state["answers"]) >= 1


def test_skip_moves_to_the_next_facet(chat_client: TestClient) -> None:
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    first_facet = state["question"]["facet"]
    response = chat_client.post(
        f"/api/v1/chat/{state['session_id']}/answer", json={"skip": True}
    )
    state = response.json()["data"]
    assert state["status"] == "asking"
    assert state["question"]["facet"] != first_facet
    # Skipping rules nothing out.
    assert state["remaining_skus"] == ["BP-HONDA", "BP-TOYOTA", "BP-BMW"]


def test_skipped_questions_stay_in_the_transcript(chat_client: TestClient) -> None:
    """A skip is a turn that happened: the conversation must accumulate it,
    not silently drop the question the user was asked."""
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    session_id = state["session_id"]

    asked = []
    for _ in range(3):
        if state["status"] != "asking":
            break
        asked.append(state["question"]["prompt"])
        state = chat_client.post(
            f"/api/v1/chat/{session_id}/answer", json={"skip": True}
        ).json()["data"]

    assert len(asked) >= 2, "need at least two questions to prove accumulation"
    # Every question asked is still in the transcript, in order.
    assert [entry["prompt"] for entry in state["answers"]] == asked
    assert all(entry["skipped"] for entry in state["answers"])
    assert all(entry["label"] == "Not sure" for entry in state["answers"])


def test_transcript_interleaves_answers_and_skips_in_order(chat_client: TestClient) -> None:
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    session_id = state["session_id"]

    first_prompt = state["question"]["prompt"]
    state = chat_client.post(
        f"/api/v1/chat/{session_id}/answer", json={"skip": True}
    ).json()["data"]

    second_prompt = state["question"]["prompt"]
    state = chat_client.post(
        f"/api/v1/chat/{session_id}/answer", json={"option_index": 0}
    ).json()["data"]

    transcript = state["answers"]
    assert [entry["prompt"] for entry in transcript][:2] == [first_prompt, second_prompt]
    assert transcript[0]["skipped"] is True
    assert transcript[1]["skipped"] is False


def test_undo_rewinds_the_trail(chat_client: TestClient) -> None:
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    session_id = state["session_id"]
    chat_client.post(f"/api/v1/chat/{session_id}/answer", json={"option_index": 0})

    response = chat_client.post(f"/api/v1/chat/{session_id}/undo", json={"keep": 0})
    state = response.json()["data"]
    assert state["answers"] == []
    assert state["remaining_skus"] == ["BP-HONDA", "BP-TOYOTA", "BP-BMW"]
    assert state["status"] == "asking"


def test_undo_counts_skips_as_turns(chat_client: TestClient) -> None:
    """`keep` indexes the transcript the client renders, so a skip occupies a
    slot exactly as an answer does."""
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    session_id = state["session_id"]
    chat_client.post(f"/api/v1/chat/{session_id}/answer", json={"skip": True})
    state = chat_client.post(
        f"/api/v1/chat/{session_id}/answer", json={"option_index": 0}
    ).json()["data"]
    assert len(state["answers"]) == 2

    # Keep only the skip.
    state = chat_client.post(
        f"/api/v1/chat/{session_id}/undo", json={"keep": 1}
    ).json()["data"]
    assert len(state["answers"]) == 1
    assert state["answers"][0]["skipped"] is True
    # The skipped facet is askable again once rewound past it.
    state = chat_client.post(
        f"/api/v1/chat/{session_id}/undo", json={"keep": 0}
    ).json()["data"]
    assert state["answers"] == []


def test_mismatch_is_surfaced_when_answers_rule_out_the_visual_leader(
    chat_client: TestClient,
) -> None:
    # 0.95 vs 0.80 — the photo has a decisive favourite (gap ≥ 0.08).
    seed = {
        "candidates": [
            {"sku": "BP-HONDA", "similarity": 0.95},
            {"sku": "BP-TOYOTA", "similarity": 0.80},
        ]
    }
    state = chat_client.post("/api/v1/chat/start", json=seed).json()["data"]
    session_id = state["session_id"]

    # Answer against the leader until it is ruled out.
    for _ in range(10):
        if state["status"] != "asking":
            break
        options = state["question"]["options"]
        index = next(
            (i for i, option in enumerate(options) if "BP-HONDA" not in option["skus"]),
            None,
        )
        if index is None:
            index = 0
        state = chat_client.post(
            f"/api/v1/chat/{session_id}/answer", json={"option_index": index}
        ).json()["data"]

    assert state["resolved_sku"] == "BP-TOYOTA"
    assert state["mismatch"] is not None
    assert state["mismatch"]["visual_leader_sku"] == "BP-HONDA"
    assert state["mismatch"]["best_survivor_sku"] == "BP-TOYOTA"


def test_bad_option_index_is_a_client_error(chat_client: TestClient) -> None:
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    response = chat_client.post(
        f"/api/v1/chat/{state['session_id']}/answer", json={"option_index": 99}
    )
    assert response.status_code == 400


def test_answer_requires_exactly_one_action(chat_client: TestClient) -> None:
    state = chat_client.post("/api/v1/chat/start", json=SEED).json()["data"]
    url = f"/api/v1/chat/{state['session_id']}/answer"
    assert chat_client.post(url, json={}).status_code == 422
    assert chat_client.post(url, json={"option_index": 0, "skip": True}).status_code == 422


def test_unknown_session_is_not_found(chat_client: TestClient) -> None:
    response = chat_client.post("/api/v1/chat/nope/answer", json={"option_index": 0})
    assert response.status_code == 404
