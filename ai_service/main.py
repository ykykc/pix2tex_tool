"""FastAPI entry point and lifecycle for the independent AI service."""

from contextlib import asynccontextmanager
import logging
from typing import Literal, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ai_service.model_manager import ModelLoadError, ModelManager
from ai_service.inference import InferenceError, InferenceService, MAX_BODY_BYTES


logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model_loaded: bool
    model: Literal["pix2tex"] = "pix2tex"


class RecognitionResponse(BaseModel):
    success: Literal[True] = True
    latex: str
    model: Literal["pix2tex"] = "pix2tex"
    processing_time: float = Field(ge=0)


def create_app(model_manager: Optional[ModelManager] = None) -> FastAPI:
    manager = model_manager if model_manager is not None else ModelManager()
    inference = InferenceService(manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            try:
                await run_in_threadpool(manager.load_model)
            except ModelLoadError as exc:
                logger.error(
                    "Pix2Tex startup failed (%s); model remains unavailable",
                    type(exc.__cause__).__name__,
                )
            yield
        finally:
            manager.unload_model()

    app = FastAPI(title="Pix2Tex Inference Service", version="0.1.0", lifespan=lifespan)
    app.state.model_manager = manager

    @app.exception_handler(InferenceError)
    async def inference_error_handler(request: Request, exc: InferenceError):
        return JSONResponse(status_code=exc.status_code, content={
            "success": False, "error": {"code": exc.code, "message": exc.message},
        })

    @app.post("/recognize", response_model=RecognitionResponse, tags=["recognition"],
              openapi_extra={"requestBody": {"required": True, "content": {
                  "multipart/form-data": {"schema": {"type": "object", "required": ["image"],
                      "properties": {"image": {"type": "string", "format": "binary"}}}}
              }}})
    async def recognize(request: Request):
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                raise InferenceError("UPLOAD_FILE_TOO_LARGE", "Request exceeds the upload limit.", 413)
            body.extend(chunk)
        return await run_in_threadpool(inference.recognize, bytes(body), request.headers.get("content-type", ""))

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(model_loaded=manager.is_loaded())

    return app


app = create_app()
