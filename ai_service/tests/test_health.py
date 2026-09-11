"""Test model startup and health with injected model factories."""

from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai_service.main import create_app
from ai_service.model_manager import ModelManager


def test_startup_loads_once_and_shutdown_unloads() -> None:
    factory = Mock(return_value=object())
    manager = ModelManager(factory)
    app = create_app(manager)
    factory.assert_not_called()
    with TestClient(app) as client:
        for _ in range(2):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok", "model_loaded": True, "model": "pix2tex"}
        factory.assert_called_once_with()
    assert not manager.is_loaded()


def test_health_available_after_startup_failure() -> None:
    manager = ModelManager(Mock(side_effect=RuntimeError("private model path")))
    with TestClient(create_app(manager)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "model_loaded": False, "model": "pix2tex"}
        assert "private" not in response.text


def test_unsupported_routes() -> None:
    with TestClient(create_app(ModelManager(lambda: object()))) as client:
        assert client.post("/health").status_code == 405
        assert client.post("/internal/v1/recognize").status_code == 404
        assert client.get("/recognize").status_code == 405
        assert client.get("/internal/v1/ready").status_code == 404


def test_import_does_not_load_model_dependencies() -> None:
    check = """
import sys
class RejectImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'pix2tex', 'torch', 'backend', 'ai_runtime'}:
            raise AssertionError('Unexpected import: ' + fullname)
        return None
sys.meta_path.insert(0, RejectImports())
from ai_service.main import app
assert not app.state.model_manager.is_loaded()
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", check],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
