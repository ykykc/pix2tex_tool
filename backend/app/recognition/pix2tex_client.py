"""Independent AI Service client; not wired into the mock recognition API."""

import asyncio
import math
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


class Pix2TexResult(BaseModel):
    success: Literal[True] = True
    latex: str
    model: Literal["pix2tex"] = "pix2tex"
    processing_time: float = Field(ge=0)


class Pix2TexClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_SERVICE_ERRORS = {
    "BAD_REQUEST": (400, "Invalid recognition request."),
    "UPLOAD_EMPTY_FILE": (400, "Image file is empty."),
    "UPLOAD_FILE_TOO_LARGE": (413, "Image exceeds the upload limit."),
    "UPLOAD_UNSUPPORTED_TYPE": (415, "Image type is not supported."),
    "UPLOAD_FILE_REQUIRED": (422, "An image file is required."),
    "UPLOAD_INVALID_IMAGE": (422, "Image cannot be decoded or is not supported."),
    "MODEL_UNAVAILABLE": (503, "AI model is unavailable."),
    "MODEL_BUSY": (503, "AI model is processing another image."),
    "RECOGNITION_FAILED": (500, "Formula recognition failed."),
    "RECOGNITION_TIMEOUT": (504, "Formula recognition timed out."),
}


class Pix2TexClient:
    def __init__(
        self, service_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        url = httpx.URL(settings.pix2tex_service_url if service_url is None else service_url)
        if url.scheme not in ("http", "https") or not url.host or url.query or url.fragment or url.userinfo:
            raise ValueError("AI Service URL must be an HTTP(S) base URL without credentials, query or fragment")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        self._url = str(url).rstrip("/") + "/recognize"
        self._timeout_seconds = timeout_seconds
        self._owns_client = client is None
        self._client = client if client is not None else httpx.AsyncClient(trust_env=False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close owned connections; injected clients remain the caller's responsibility."""
        if self._owns_client:
            await self._client.aclose()

    async def recognize(
        self, image: bytes, filename: str = "formula.png", content_type: str = "image/png",
    ) -> Pix2TexResult:
        """Upload image bytes once and validate the AI Service response. No retries."""
        try:
            response = await asyncio.wait_for(
                self._client.post(
                    self._url, files={"image": (filename, image, content_type)},
                    timeout=httpx.Timeout(self._timeout_seconds, connect=min(2.0, self._timeout_seconds)),
                    follow_redirects=False,
                ),
                timeout=self._timeout_seconds,
            )
        except httpx.ConnectTimeout as exc:
            raise Pix2TexClientError("MODEL_UNAVAILABLE", "AI Service connection timed out.") from exc
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            raise Pix2TexClientError("RECOGNITION_TIMEOUT", "AI Service request timed out.") from exc
        except httpx.RequestError as exc:
            raise Pix2TexClientError("MODEL_UNAVAILABLE", "Cannot reach AI Service.") from exc

        try:
            body = response.json()
        except (ValueError, UnicodeError) as exc:
            raise Pix2TexClientError("RECOGNITION_FAILED", "AI Service returned invalid JSON.") from exc

        if isinstance(body, dict) and body.get("success") is False:
            error = body.get("error")
            if isinstance(error, dict) and isinstance(error.get("code"), str):
                known = _SERVICE_ERRORS.get(error["code"])
                if (known and response.status_code == known[0]
                        and isinstance(error.get("message"), str) and error["message"].strip()):
                    raise Pix2TexClientError(error["code"], known[1])
        elif response.status_code == 200 and isinstance(body, dict) and body.get("success") is True:
            latex = body.get("latex")
            elapsed = body.get("processing_time")
            if (isinstance(latex, str) and latex.strip() and body.get("model") == "pix2tex"
                    and type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0):
                return Pix2TexResult(latex=latex, processing_time=elapsed)

        raise Pix2TexClientError("RECOGNITION_FAILED", "AI Service returned an unexpected response.")
