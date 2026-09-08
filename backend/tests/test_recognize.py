from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app
from app.recognition.adapter import MOCK_LATEX


client = TestClient(app)


def make_png_bytes() -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (32, 32), "white")
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_recognize_returns_mock_latex_for_valid_image() -> None:
    response = client.post(
        "/api/v1/recognize",
        files={"file": ("formula.png", make_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["latex"] == MOCK_LATEX
    assert body["data"]["processing_time"] >= 0
    assert body["error"] is None


def test_recognize_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/api/v1/recognize",
        files={"file": ("formula.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UPLOAD_UNSUPPORTED_TYPE"


def test_recognize_rejects_empty_image_file() -> None:
    response = client.post(
        "/api/v1/recognize",
        files={"file": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UPLOAD_EMPTY_FILE"


def test_recognize_rejects_oversized_file() -> None:
    response = client.post(
        "/api/v1/recognize",
        files={
            "file": (
                "large.png",
                b"0" * (settings.max_upload_size_bytes + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 413
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UPLOAD_FILE_TOO_LARGE"


def test_recognize_rejects_unreadable_image() -> None:
    response = client.post(
        "/api/v1/recognize",
        files={"file": ("broken.png", b"not really png", "image/png")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UPLOAD_INVALID_IMAGE"

