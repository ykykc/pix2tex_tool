"""Lifecycle tests without model dependencies or network access."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from ai_service.model_manager import ModelLoadError, ModelManager


def test_unloaded_access_does_not_initialize() -> None:
    factory = Mock()
    manager = ModelManager(factory)
    assert not manager.is_loaded()
    with pytest.raises(RuntimeError, match="not loaded"):
        manager.get_model()
    factory.assert_not_called()


def test_repeated_and_concurrent_loads_share_one_model() -> None:
    model = object()
    factory = Mock(return_value=model)
    manager = ModelManager(factory)
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: manager.load_model(), range(12)))
    factory.assert_called_once_with()
    assert manager.is_loaded()
    assert manager.get_model() is model


def test_failure_leaves_unloaded_and_allows_retry() -> None:
    model = object()
    manager = ModelManager(Mock(side_effect=[ValueError("load error"), model]))
    with pytest.raises(ModelLoadError) as error:
        manager.load_model()
    assert isinstance(error.value.__cause__, ValueError)
    assert not manager.is_loaded()
    manager.load_model()
    assert manager.get_model() is model


def test_none_result_is_not_loaded() -> None:
    manager = ModelManager(lambda: None)
    with pytest.raises(ModelLoadError):
        manager.load_model()
    assert not manager.is_loaded()


def test_unload_is_idempotent_and_can_reload() -> None:
    factory = Mock(side_effect=[object(), object()])
    manager = ModelManager(factory)
    manager.load_model()
    first = manager.get_model()
    manager.unload_model()
    manager.unload_model()
    assert not manager.is_loaded()
    manager.load_model()
    assert manager.get_model() is not first


def test_missing_dependency_fails_cleanly() -> None:
    with patch("ai_service.model_manager.importlib.util.find_spec", return_value=None):
        manager = ModelManager()
        with pytest.raises(ModelLoadError):
            manager.load_model()
    assert not manager.is_loaded()


def test_missing_resources_fail_before_model_import(tmp_path) -> None:
    spec = SimpleNamespace(origin=str(tmp_path / "pix2tex" / "__init__.py"))
    with patch("ai_service.model_manager.importlib.util.find_spec", return_value=spec):
        manager = ModelManager()
        with pytest.raises(ModelLoadError) as error:
            manager.load_model()
    assert "Required local model resource" in str(error.value.__cause__)
    assert not manager.is_loaded()
