import unittest

from fastapi.testclient import TestClient

from app.main import app


class HealthEndpointTest(unittest.TestCase):
    def test_health_endpoint_returns_success_envelope(self) -> None:
        client = TestClient(app)

        response = client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["success"], True)
        self.assertEqual(body["data"]["status"], "ok")
        self.assertEqual(body["data"]["service"], "latex-web-tool-api")
        self.assertIsNone(body["error"])
        self.assertTrue(body["meta"]["request_id"].startswith("req_"))


if __name__ == "__main__":
    unittest.main()

