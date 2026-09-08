# Architecture

## Overview

Latex Web Tool is a formula recognition web platform. The target workflow is:

```text
Formula image -> backend upload validation -> recognition module -> LaTeX -> conversion module -> MathML -> frontend preview
```

The current project is in the early backend MVP stage. The backend already provides a FastAPI application skeleton, a health endpoint, and a mock formula recognition endpoint. The mock endpoint validates uploaded image files and returns fixed LaTeX through a project-owned recognition adapter.

Pix2Tex, real LaTeX recognition, MathML conversion, frontend pages, database storage, and AI explanation are not implemented yet.

## System Layers

The system should stay layered so each part can evolve independently.

```text
Frontend Web App
  |
  | HTTP multipart/form-data / JSON
  v
Backend API
  |
  | validates request and coordinates services
  v
Service Layer
  |
  | calls recognition and conversion boundaries
  v
Recognition Module       Conversion Module
  |                       |
  | Pix2Tex adapter       | LaTeX to MathML adapter
  v                       v
Third-party model         Third-party converter or local conversion logic
```

## Frontend Responsibilities

The frontend will be responsible for user-facing interaction:

- Let users upload one formula image.
- Show local image preview before or after upload.
- Call backend REST APIs.
- Display returned LaTeX.
- Display returned MathML.
- Render online formula preview from LaTeX using a frontend rendering library such as KaTeX or MathJax.
- Later show AI explanations and generated technical document content.

The frontend should not call Pix2Tex directly. It should treat formula recognition as a backend API capability.

## Backend Responsibilities

The backend is responsible for API and workflow orchestration:

- Expose versioned REST APIs under `/api/v1`.
- Validate uploaded files before recognition.
- Keep API responses in a consistent JSON envelope.
- Route requests to service-layer modules.
- Keep route handlers thin.
- Hide Pix2Tex and other third-party implementation details from API consumers.
- Return user-friendly errors instead of stack traces.
- Later coordinate LaTeX-to-MathML conversion, AI explanation, document generation, and optional persistence.

## Recognition Module Relationship

The recognition module owns formula recognition boundaries.

Current state:

- `backend/app/recognition/adapter.py` contains a mock adapter.
- The adapter returns fixed test LaTeX.
- Pix2Tex is not called yet.

Future state:

- The same module should host the Pix2Tex adapter.
- Model loading, preprocessing, inference, postprocessing, timeout handling, and model errors should remain hidden behind this adapter boundary.
- Third-party Pix2Tex source code must not be directly modified.

The backend service layer should depend on the project-owned adapter interface, not on Pix2Tex internals.

## Conversion Module Relationship

The conversion module will convert recognized LaTeX into MathML.

Current state:

- MathML conversion is not implemented.
- The mock recognition endpoint currently returns only LaTeX and processing time.

Future state:

- Add a backend conversion module, for example `backend/app/conversion/`.
- Keep LaTeX-to-MathML conversion behind a project-owned service or adapter.
- If MathML conversion fails after LaTeX recognition succeeds, return LaTeX and include a non-fatal warning instead of failing the whole recognition request.
- Keep the frontend preview based on LaTeX so preview rendering is not blocked by MathML conversion failure.

## Current Backend Module Structure

Current backend structure:

```text
backend/
  README.md
  pyproject.toml
  app/
    __init__.py
    main.py
    api/
      __init__.py
      router.py
      routes/
        __init__.py
        health.py
        recognize.py
    core/
      __init__.py
      config.py
      errors.py
    recognition/
      __init__.py
      adapter.py
    schemas/
      __init__.py
      recognition.py
    services/
      __init__.py
      recognition_service.py
  tests/
    __init__.py
    test_health.py
    test_recognize.py
```

### Module Roles

`backend/app/main.py`

- Creates the FastAPI application.
- Registers the API router.
- Registers API error handling.
- Configures OpenAPI and Swagger paths.

`backend/app/api/router.py`

- Collects route modules.
- Registers route groups under the shared API router.

`backend/app/api/routes/health.py`

- Defines `GET /api/v1/health`.
- Checks whether the backend API is alive.

`backend/app/api/routes/recognize.py`

- Defines `POST /api/v1/recognize`.
- Accepts multipart image uploads.
- Delegates business logic to the service layer.

`backend/app/core/config.py`

- Stores application settings.
- Defines API prefix, upload size limit, and supported image content types.

`backend/app/core/errors.py`

- Defines project-owned API errors.
- Supports consistent error responses.

`backend/app/services/recognition_service.py`

- Owns mock recognition workflow orchestration.
- Validates upload content type, file size, and image readability.
- Calls the recognition adapter.
- Builds the API response model.

`backend/app/recognition/adapter.py`

- Contains the current mock recognition adapter.
- Is the future Pix2Tex integration point.

`backend/app/schemas/recognition.py`

- Defines Pydantic models for validated upload metadata and recognition responses.

`backend/tests/`

- Contains backend API tests.
- Covers health and mock recognition behavior.

## API Shape

Current implemented endpoints:

```text
GET  /api/v1/health
POST /api/v1/recognize
```

Current documentation endpoints:

```text
GET /api/v1/docs
GET /api/v1/openapi.json
```

The current mock recognition endpoint is intentionally smaller than the final MVP API contract in `docs/api-design.md`. It exists to prove the backend API loop first.

Future API alignment work should decide whether the final recognition path is:

```text
POST /api/v1/recognize
```

or:

```text
POST /api/v1/formulas/recognize
```

After that decision, `docs/api-design.md`, tests, and route names should be aligned in one focused task.

## Future Pix2Tex Integration Position

Pix2Tex should be integrated at:

```text
backend/app/recognition/adapter.py
```

or, if the module grows:

```text
backend/app/recognition/
  adapter.py
  pix2tex_adapter.py
  preprocessing.py
  result.py
```

Recommended future responsibilities:

- `preprocessing.py`: normalize uploaded images before inference.
- `pix2tex_adapter.py`: load Pix2Tex and run inference.
- `result.py`: define internal recognition result objects if needed.
- `adapter.py`: expose the stable project-owned recognition interface.

The service layer should keep calling a project adapter method such as `recognize(image)`. Replacing the mock adapter with Pix2Tex should not require route-level changes.

## Future AI Explanation Extension Position

AI explanation should be added after the core recognition workflow is stable.

Recommended future structure:

```text
backend/app/ai/
  __init__.py
  explanation_service.py
  prompts.py
  schemas.py
```

Possible API routes:

```text
POST /api/v1/formulas/{formula_id}/explain
POST /api/v1/explanations
```

AI explanation should depend on recognized LaTeX and optional MathML, not on the uploaded image directly unless a later design explicitly requires multimodal explanation.

The AI module should return structured output, such as:

- Formula summary.
- Variable explanations.
- Step-by-step interpretation.
- Optional technical document fragments.

## Future Deployment Shape

MVP deployment can remain simple:

```text
Browser frontend -> FastAPI backend -> in-process mock or Pix2Tex adapter
```

After Pix2Tex is integrated and performance needs are clearer, the recognition runtime may be separated:

```text
Browser frontend -> FastAPI backend -> recognition service -> Pix2Tex model runtime
```

Reasons to split the recognition service later:

- Avoid blocking the main API process during model loading.
- Isolate GPU or heavy CPU dependencies.
- Add recognition queues and concurrency limits.
- Scale frontend/API and model inference independently.

This split is not required for the current backend API loop.

## Architecture Rules

- Keep routes thin.
- Keep validation and workflow logic in services.
- Keep third-party model details behind project-owned adapters.
- Keep conversion logic separate from recognition logic.
- Keep frontend preview rendering separate from backend recognition.
- Add tests for every new feature.
- Update documentation when module boundaries, APIs, or workflow decisions change.

