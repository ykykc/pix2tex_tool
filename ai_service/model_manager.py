"""Own one model instance; import heavy dependencies only when loading."""

import importlib.util
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Optional


class ModelLoadError(RuntimeError):
    """Initialization failed and the manager remains unloaded."""


def _create_latex_ocr() -> Any:
    spec = importlib.util.find_spec("pix2tex")
    if spec is None or spec.origin is None:
        raise RuntimeError("Pix2Tex is not installed in this Python environment")
    root = Path(spec.origin).resolve().parent / "model"
    # Check the validated package layout before its automatic download path.
    for relative in (
        "settings/config.yaml", "dataset/tokenizer.json",
        "checkpoints/weights.pth", "checkpoints/image_resizer.pth",
    ):
        resource = root / relative
        if not resource.is_file() or resource.stat().st_size == 0:
            raise RuntimeError(f"Required local model resource is missing: {relative}")
    logger = logging.getLogger()
    previous_level = logger.level
    try:
        from pix2tex.cli import LatexOCR

        return LatexOCR()
    finally:
        # LatexOCR changes the process root log level during initialization.
        logger.setLevel(previous_level)


class ModelManager:
    def __init__(self, model_factory: Optional[Callable[[], Any]] = None) -> None:
        self._factory = model_factory if model_factory is not None else _create_latex_ocr
        self._model: Optional[Any] = None
        self._lock = Lock()

    def load_model(self) -> None:
        """Load once; publish only a fully initialized instance. Failure permits retry."""
        with self._lock:
            if self._model is not None:
                return
            try:
                model = self._factory()
                if model is None:
                    raise ValueError("Model factory returned no model")
            except Exception as exc:
                raise ModelLoadError("Pix2Tex model initialization failed") from exc
            self._model = model

    def get_model(self) -> Any:
        """Return the loaded instance without implicit initialization."""
        with self._lock:
            if self._model is None:
                raise RuntimeError("Pix2Tex model is not loaded")
            return self._model

    def is_loaded(self) -> bool:
        return self._model is not None

    def unload_model(self) -> None:
        """Release this manager's reference; allocator cleanup is not guaranteed."""
        with self._lock:
            self._model = None
