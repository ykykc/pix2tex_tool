"""API tests with repository fixtures; real inference is explicitly opt-in."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import os
from pathlib import Path
from threading import Event
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient
from PIL import Image

from ai_service.main import create_app
from ai_service.model_manager import ModelManager


SAMPLES = Path(__file__).resolve().parents[2] / "ai_runtime" / "samples" / "test_cases"
SAMPLE = SAMPLES / "basic" / "formula_quadratic.png"


class RecognizeTests(unittest.TestCase):
    def setUp(self):
        self.model = Mock(return_value=r"x^{2}+2x+1=0")
        self.factory = Mock(return_value=self.model)
        self.manager = ModelManager(self.factory)
        self.client = TestClient(create_app(self.manager))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def upload(self, content=None, mime="image/png", field="image"):
        return self.client.post("/recognize", files={
            field: ("formula.png", SAMPLE.read_bytes() if content is None else content, mime)
        })

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        body = response.json()
        self.assertEqual(set(body), {"success", "error"})
        self.assertIs(body["success"], False)
        self.assertEqual(body["error"]["code"], code)
        self.assertIsInstance(body["error"]["message"], str)

    def test_existing_samples_and_reuse(self):
        samples = sorted(SAMPLES.glob("*/*.png"))
        self.assertGreaterEqual(len(samples), 4)
        for sample in samples:
            with self.subTest(sample=sample.name):
                response = self.upload(sample.read_bytes())
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(set(body), {"success", "latex", "model", "processing_time"})
                self.assertTrue(body["success"])
                self.assertEqual(body["latex"], r"x^{2}+2x+1=0")
                self.assertEqual(body["model"], "pix2tex")
                self.assertGreaterEqual(body["processing_time"], 0)
        self.factory.assert_called_once_with()

    def test_missing_image_field(self):
        self.assert_error(self.upload(field="file"), 422, "UPLOAD_FILE_REQUIRED")

    def test_wrong_request_type(self):
        self.assert_error(self.client.post("/recognize", json={}), 415, "UPLOAD_UNSUPPORTED_TYPE")

    def test_empty_image(self):
        self.assert_error(self.upload(b""), 400, "UPLOAD_EMPTY_FILE")

    def test_corrupt_image(self):
        self.assert_error(self.upload(b"broken"), 422, "UPLOAD_INVALID_IMAGE")
        self.model.assert_not_called()

    def test_unsupported_type(self):
        self.assert_error(self.upload(mime="text/plain"), 415, "UPLOAD_UNSUPPORTED_TYPE")

    def test_mime_mismatch(self):
        self.assert_error(self.upload(mime="image/jpeg"), 422, "UPLOAD_INVALID_IMAGE")

    def test_oversized_upload(self):
        self.assert_error(self.upload(b"x" * (5 * 1024 * 1024 + 1)), 413, "UPLOAD_FILE_TOO_LARGE")

    def test_oversized_body(self):
        self.assert_error(self.upload(b"x" * (6 * 1024 * 1024)), 413, "UPLOAD_FILE_TOO_LARGE")

    def test_bad_boundary(self):
        response = self.client.post("/recognize", content=b"broken", headers={
            "Content-Type": "multipart/form-data; boundary=missing"})
        self.assert_error(response, 400, "BAD_REQUEST")

    def test_multiple_files(self):
        response = self.client.post("/recognize", files=[
            ("image", ("a.png", SAMPLE.read_bytes(), "image/png")),
            ("image", ("b.png", SAMPLE.read_bytes(), "image/png")),
        ])
        self.assert_error(response, 400, "BAD_REQUEST")

    def test_unavailable_model(self):
        self.manager.unload_model()
        self.assert_error(self.upload(), 503, "MODEL_UNAVAILABLE")
        self.factory.assert_called_once_with()

    def test_model_failure_and_empty_results(self):
        self.model.side_effect = RuntimeError("private path")
        response = self.upload()
        self.assert_error(response, 500, "RECOGNITION_FAILED")
        self.assertNotIn("private", response.text)
        self.model.side_effect = None
        for value in (None, "", "  "):
            self.model.return_value = value
            self.assert_error(self.upload(), 500, "RECOGNITION_FAILED")

    def test_transparency_and_cleanup(self):
        stream = BytesIO()
        with Image.new("RGBA", (32, 32), (0, 0, 0, 0)) as source:
            source.save(stream, format="PNG")

        def infer(image):
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
            self.model.last_pic = image.copy()
            return "x"

        self.model.side_effect = infer
        self.assertEqual(self.upload(stream.getvalue()).status_code, 200)
        self.assertIsNone(self.model.last_pic)

    def test_busy_request_and_health(self):
        entered, release = Event(), Event()

        def infer(image):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("Test release timeout")
            return "x"

        self.model.side_effect = infer
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.upload)
            try:
                self.assertTrue(entered.wait(5))
                self.assert_error(self.upload(), 503, "MODEL_BUSY")
                self.assertEqual(self.client.get("/health").status_code, 200)
            finally:
                release.set()
            self.assertEqual(pending.result(timeout=5).status_code, 200)


@unittest.skipUnless(os.environ.get("AI_SERVICE_REAL_MODEL_TEST") == "1", "Real model test is opt-in")
class RealRecognitionTests(unittest.TestCase):
    def test_real_model_with_existing_images(self):
        manager = ModelManager()
        with TestClient(create_app(manager)) as client:
            self.assertTrue(manager.is_loaded())
            instance = manager.get_model()
            for sample in sorted(SAMPLES.glob("*/*.png")):
                with self.subTest(sample=sample.name):
                    response = client.post("/recognize", files={
                        "image": (sample.name, sample.read_bytes(), "image/png")})
                    self.assertEqual(response.status_code, 200, response.text)
                    body = response.json()
                    self.assertTrue(body["success"])
                    self.assertIsInstance(body["latex"], str)
                    self.assertTrue(body["latex"].strip())
                    self.assertEqual(body["model"], "pix2tex")
                    self.assertGreaterEqual(body["processing_time"], 0)
                    self.assertIs(manager.get_model(), instance)
                    self.assertIsNone(instance.last_pic)
                    print(sample.name, response.text, flush=True)


if __name__ == "__main__":
    unittest.main()
