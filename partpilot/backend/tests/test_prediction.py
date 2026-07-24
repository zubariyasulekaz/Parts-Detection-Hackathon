"""Tests for the /predict endpoint.

The orchestrator is replaced with a fake via dependency override so these
tests exercise the HTTP/router wiring without pulling in the heavy AI
dependencies (tensorflow, rembg, faiss, open_clip) or a trained model.
"""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.api.dependencies import get_orchestrator
from backend.app import create_app
from backend.pipeline.orchestrator import OrchestratorResult
from backend.schemas.prediction import PredictionResponse, SearchResult


class _FakeOrchestrator:
    """Returns a canned prediction, ignoring the actual image."""

    def run(self, image, top_k=10, explain=False, remove_bg=True):  # noqa: ANN001, D102
        return OrchestratorResult(
            prediction=PredictionResponse(
                predicted_category="Oil Filter",
                confidence=0.93,
                search_time_ms=12.3,
                results=[
                    SearchResult(sku="3978", similarity_score=0.88),
                    SearchResult(sku="S45011", similarity_score=0.71),
                ][:top_k],
            )
        )


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_orchestrator] = _FakeOrchestrator
    return TestClient(app)


def _png_bytes(color: tuple[int, int, int] = (120, 120, 120)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(buf, "PNG")
    return buf.getvalue()


def test_predict_returns_top_matches(client: TestClient) -> None:
    response = client.post(
        "/api/v1/predict",
        files={"file": ("part.png", io.BytesIO(_png_bytes()), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["predicted_category"] == "Oil Filter"
    assert data["confidence"] == pytest.approx(0.93)
    assert [r["sku"] for r in data["results"]] == ["3978", "S45011"]
    assert data["results"][0]["similarity_score"] == pytest.approx(0.88)
    assert "Best match: 3978" in body["message"]


def test_predict_respects_top_k(client: TestClient) -> None:
    response = client.post(
        "/api/v1/predict?top_k=1",
        files={"file": ("part.png", io.BytesIO(_png_bytes()), "image/png")},
    )

    assert response.status_code == 200
    assert len(response.json()["data"]["results"]) == 1


def test_predict_rejects_invalid_image(client: TestClient) -> None:
    response = client.post(
        "/api/v1/predict",
        files={"file": ("bad.jpg", io.BytesIO(b"not-a-real-image"), "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_IMAGE"
