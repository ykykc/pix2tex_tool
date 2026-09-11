# Backend

FastAPI backend for the Latex Web Tool formula recognition platform.

Current scope:

- FastAPI application entrypoint.
- Configuration module.
- API route structure.
- MVP health endpoint.
- Mock formula recognition endpoint.
- Multipart image upload validation for the mock recognition endpoint.
- Standalone async AI Service HTTP client, not yet connected to the API.

Not implemented yet:

- Connecting the existing recognition API to Pix2Tex.
- Real LaTeX recognition.
- MathML conversion.
- Database.
- Frontend pages.

## Requirements

- Python 3.9 or newer.

## Install Dependencies

From the `backend` directory:

```powershell
python -m pip install -e .[dev]
```

For runtime-only dependencies:

```powershell
python -m pip install -e .
```

## Start Development Server

From the `backend` directory:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
GET http://127.0.0.1:8000/api/v1/health
```

Mock formula recognition:

```text
POST http://127.0.0.1:8000/api/v1/recognize
Content-Type: multipart/form-data

file=<formula image>
```

API docs:

```text
http://127.0.0.1:8000/api/v1/docs
```

## Run Tests

The current startup test uses Python standard library `unittest`:

```powershell
python -m unittest discover tests
```

After installing development dependencies, `pytest` can also be used:

```powershell
python -m pytest
```

## AI Service Client (Phase 4.1)

`app/recognition/pix2tex_client.py` defines `Pix2TexClient` independently of the
existing Mock adapter. Existing routes and service wiring remain unchanged.
The client uses HTTPX as a runtime dependency, with no model dependencies.

Set `PIX2TEX_SERVICE_URL` before starting Python to override the default
`http://127.0.0.1:8001`. `Settings.pix2tex_service_url` reads that environment
variable when settings are constructed. The URL is a trusted service base URL,
not a user-supplied upload parameter. `/recognize` is appended to it.

Within an async caller:

```python
from app.recognition.pix2tex_client import Pix2TexClient

async def recognize_image(image_bytes):
    async with Pix2TexClient() as client:
        return await client.recognize(
            image_bytes, filename="formula.png", content_type="image/png"
        )
```

The caller reads its image into bytes and supplies the correct MIME type.
The client sends multipart field `image`; it does not send the Backend API's
`file` field. It returns a validated `Pix2TexResult` with `success`, `latex`,
`model`, and AI Service `processing_time` in seconds. That timing is not the
total Backend request duration. Upload validation remains the caller/service's
responsibility; the client neither loads models nor stores files.

`Pix2TexClientError` exposes `code` and a sanitized `message`. Known AI Service
errors are preserved by code; connection failures map to `MODEL_UNAVAILABLE`,
request timeouts to `RECOGNITION_TIMEOUT`, and malformed/unexpected responses to
`RECOGNITION_FAILED`. There is no automatic retry, redirect following or Mock
fallback. Timeout defaults to 30 seconds total with a 2-second connection limit;
`timeout_seconds` can override the budget. Cancellation cannot stop upstream
inference that has already started.

Reuse one client for multiple calls when integrating later; call `aclose()` at
shutdown or use its async context manager. An injected `httpx.AsyncClient`
remains owned by its caller. Production-owned clients ignore proxy environment
variables for the local AI connection. Client tests use `httpx.MockTransport`
and do not require a running AI Service, network access, or new dependencies.
