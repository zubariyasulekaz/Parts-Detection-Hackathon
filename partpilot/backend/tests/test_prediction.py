"""Tests for the /predict endpoint.

Only exercises the dummy placeholder response — once Brain 1-3 are
implemented, extend this with real fixture images and assertions
against actual predictions.
"""

import io

from fastapi.testclient import TestClient


def test_predict_returns_dummy_response(client: TestClient) -> None:
    fake_image = io.BytesIO(b"not-a-real-image-just-bytes-for-the-dummy-endpoint")

    response = client.post(
        "/api/v1/predict",
        files={"file": ("part.jpg", fake_image, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "predicted_category" in body["data"]


# TODO: Once Brain 1-3 are implemented, add tests covering:
#   - Rejecting invalid/corrupt image uploads (400).
#   - Rejecting oversized uploads (400).
#   - Real classification + similarity search results for known fixtures.
