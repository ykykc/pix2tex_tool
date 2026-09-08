# API Design

## Scope

This document defines the first REST API design for the MVP stage of the formula recognition web platform.

MVP core workflow:

1. Upload an image containing a mathematical formula.
2. Recognize the formula with Pix2Tex.
3. Return LaTeX.
4. Convert and return MathML.
5. Let the frontend render an online preview from the returned LaTeX.

This document is only an API design document. It does not define frontend or backend implementation code.

## Design Principles

- Keep the MVP API small and stable.
- Use REST-style paths with version prefix `/api/v1`.
- Use JSON responses for both success and error results.
- Use `multipart/form-data` for image upload.
- Do not expose Pix2Tex internal implementation details through the public API.
- Keep LaTeX recognition and MathML conversion in one MVP endpoint to support the simplest user flow.
- Reserve extension endpoints for later AI explanation, document generation, async tasks, and batch recognition.

## Base Path

All MVP endpoints use:

```text
/api/v1
```

## Response Envelope

All API responses should use a consistent JSON envelope.

Success response:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

Error response:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message.",
    "details": {}
  },
  "meta": {
    "request_id": "req_01HZX..."
  }
}
```

## MVP Endpoint Summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Check whether the backend API is alive. |
| `GET` | `/api/v1/model/status` | Check whether the formula recognition model is available. |
| `POST` | `/api/v1/formulas/recognize` | Upload one formula image and return LaTeX plus MathML. |

## Endpoint: Health Check

### Path

```text
GET /api/v1/health
```

### Purpose

Check whether the backend API process is running.

This endpoint does not check whether Pix2Tex is loaded or usable.

### Request Parameters

No request parameters.

### Success Response

HTTP status: `200 OK`

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "latex-web-tool-api"
  },
  "error": null,
  "meta": {
    "request_id": "req_01HZX000000000000000000000"
  }
}
```

### Error Response

This endpoint should normally return `200 OK` if the API process is reachable.

## Endpoint: Model Status

### Path

```text
GET /api/v1/model/status
```

### Purpose

Check whether the formula recognition model dependency is available.

For the MVP, this endpoint should report high-level readiness only. It should not expose local model paths, private configuration, stack traces, GPU details, or third-party library internals.

### Request Parameters

No request parameters.

### Success Response

HTTP status: `200 OK`

```json
{
  "success": true,
  "data": {
    "status": "ready",
    "recognition_engine": "pix2tex",
    "supports": {
      "latex": true,
      "mathml": true
    }
  },
  "error": null,
  "meta": {
    "request_id": "req_01HZX000000000000000000001"
  }
}
```

### Possible Status Values

| Value | Meaning |
| --- | --- |
| `ready` | The model can accept recognition requests. |
| `loading` | The model is being initialized. |
| `unavailable` | The model cannot currently serve recognition requests. |

### Error Response

If the API is alive but the model is unavailable, prefer HTTP `200 OK` with `data.status = "unavailable"` instead of treating this endpoint as a failed request.

Use HTTP `500 Internal Server Error` only when the status check itself fails unexpectedly.

## Endpoint: Formula Recognition

### Path

```text
POST /api/v1/formulas/recognize
```

### Purpose

Upload one image containing a mathematical formula, recognize it through Pix2Tex, and return both LaTeX and MathML.

This is the main MVP endpoint.

### Request Content Type

```text
multipart/form-data
```

### Request Parameters

| Name | Location | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `file` | form-data | file | Yes | Formula image file. |
| `include_mathml` | form-data | boolean | No | Whether to return MathML. Defaults to `true` in MVP. |
| `include_metadata` | form-data | boolean | No | Whether to return timing and processing metadata. Defaults to `true`. |

### MVP Request Example

```text
POST /api/v1/formulas/recognize
Content-Type: multipart/form-data

file=<formula image>
include_mathml=true
include_metadata=true
```

### Success Response

HTTP status: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": "formula_01HZX000000000000000000000",
    "latex": "\\frac{a}{b}=c",
    "mathml": "<math><mfrac><mi>a</mi><mi>b</mi></mfrac><mo>=</mo><mi>c</mi></math>",
    "preview": {
      "render_format": "latex",
      "source": "\\frac{a}{b}=c"
    },
    "warnings": []
  },
  "error": null,
  "meta": {
    "request_id": "req_01HZX000000000000000000002",
    "processing_time_ms": 850,
    "recognition_time_ms": 720,
    "conversion_time_ms": 25
  }
}
```

### Success Response Fields

| Field | Type | Description |
| --- | --- | --- |
| `data.id` | string | Server-generated recognition result ID for current response tracking. Persistence is not required in MVP. |
| `data.latex` | string | Recognized LaTeX formula. |
| `data.mathml` | string or null | Converted MathML. Null when `include_mathml=false` or conversion fails non-fatally. |
| `data.preview.render_format` | string | Preview source type. MVP value is `latex`. |
| `data.preview.source` | string | Formula source for frontend preview rendering. Usually the same as `data.latex`. |
| `data.warnings` | array | Non-fatal warnings, such as MathML conversion failure. |
| `meta.request_id` | string | Request identifier for troubleshooting. |
| `meta.processing_time_ms` | number | Total request processing time. |
| `meta.recognition_time_ms` | number | Pix2Tex recognition time. |
| `meta.conversion_time_ms` | number or null | LaTeX-to-MathML conversion time. |

### Non-Fatal MathML Conversion Failure

If LaTeX recognition succeeds but MathML conversion fails, the endpoint should still return HTTP `200 OK`.

```json
{
  "success": true,
  "data": {
    "id": "formula_01HZX000000000000000000003",
    "latex": "\\text{recognized latex}",
    "mathml": null,
    "preview": {
      "render_format": "latex",
      "source": "\\text{recognized latex}"
    },
    "warnings": [
      {
        "code": "MATHML_CONVERSION_FAILED",
        "message": "LaTeX was recognized, but MathML conversion failed."
      }
    ]
  },
  "error": null,
  "meta": {
    "request_id": "req_01HZX000000000000000000003",
    "processing_time_ms": 900,
    "recognition_time_ms": 760,
    "conversion_time_ms": null
  }
}
```

## File Upload Limits

MVP upload limits:

| Limit | MVP Value |
| --- | --- |
| Maximum files per request | 1 |
| Supported formats | PNG, JPG, JPEG, WEBP |
| Maximum file size | 5 MB |
| Minimum image size | 16 x 16 px |
| Maximum image size | 4096 x 4096 px |
| Empty file | Rejected |
| Animated image | Use first frame only or reject. MVP recommendation: reject. |
| Filename trust | Do not trust filename for validation. Validate actual image content. |
| Persistence | Do not permanently store uploaded images in MVP. |

Validation should check both declared content type and actual decoded image content.

Accepted MIME types:

```text
image/png
image/jpeg
image/webp
```

Rejected examples:

- Non-image files.
- Empty files.
- Corrupted images.
- Images exceeding size limits.
- Images below minimum dimensions.
- Images above maximum dimensions.
- Multiple files in one MVP request.

## Error Code Design

### Error Response Structure

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "UPLOAD_FILE_TOO_LARGE",
    "message": "Uploaded file exceeds the maximum size of 5 MB.",
    "details": {
      "max_size_mb": 5
    }
  },
  "meta": {
    "request_id": "req_01HZX000000000000000000004"
  }
}
```

### MVP Error Codes

| HTTP Status | Code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `BAD_REQUEST` | Request format is invalid. |
| `400 Bad Request` | `UPLOAD_FILE_REQUIRED` | No file was provided. |
| `400 Bad Request` | `UPLOAD_MULTIPLE_FILES_NOT_SUPPORTED` | More than one file was uploaded. |
| `400 Bad Request` | `UPLOAD_EMPTY_FILE` | Uploaded file is empty. |
| `413 Payload Too Large` | `UPLOAD_FILE_TOO_LARGE` | Uploaded file exceeds the configured size limit. |
| `415 Unsupported Media Type` | `UPLOAD_UNSUPPORTED_TYPE` | File type is not supported. |
| `422 Unprocessable Entity` | `UPLOAD_INVALID_IMAGE` | File cannot be decoded as a valid image. |
| `422 Unprocessable Entity` | `UPLOAD_IMAGE_TOO_SMALL` | Image dimensions are below the minimum size. |
| `422 Unprocessable Entity` | `UPLOAD_IMAGE_TOO_LARGE` | Image dimensions exceed the maximum size. |
| `503 Service Unavailable` | `MODEL_UNAVAILABLE` | Pix2Tex is unavailable or not initialized. |
| `504 Gateway Timeout` | `RECOGNITION_TIMEOUT` | Recognition exceeded the configured timeout. |
| `500 Internal Server Error` | `RECOGNITION_FAILED` | Recognition failed unexpectedly. |
| `500 Internal Server Error` | `INTERNAL_ERROR` | Unexpected server error. |

### Warning Codes

Warning codes are returned inside successful responses when the main recognition flow succeeds.

| Code | Meaning |
| --- | --- |
| `MATHML_CONVERSION_FAILED` | LaTeX recognition succeeded, but MathML conversion failed. |
| `LATEX_NORMALIZED` | The recognized LaTeX was normalized before response. |
| `LOW_CONFIDENCE_RESULT` | The model result may be unreliable if confidence information becomes available later. |

## Recognition Timeout

MVP recommendation:

| Item | Value |
| --- | --- |
| Recognition timeout | 30 seconds |
| MathML conversion timeout | 5 seconds |
| Total request timeout | 40 seconds |

If recognition times out, return:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "RECOGNITION_TIMEOUT",
    "message": "Formula recognition timed out. Please try again with a clearer or smaller image.",
    "details": {
      "timeout_seconds": 30
    }
  },
  "meta": {
    "request_id": "req_01HZX000000000000000000005"
  }
}
```

## Frontend Preview Contract

The backend does not need to return rendered HTML in the MVP.

The frontend should render the preview from:

```json
{
  "render_format": "latex",
  "source": "\\frac{a}{b}=c"
}
```

This keeps rendering concerns in the frontend and avoids coupling the API to a specific preview library.

## Security and Privacy Rules

MVP API rules:

- Do not permanently store uploaded images unless a later task explicitly designs persistence.
- Do not return local file paths in responses.
- Do not expose model stack traces to the frontend.
- Do not trust uploaded filenames.
- Validate image content by decoding it.
- Limit upload size and image dimensions.
- Generate `request_id` values for debugging.

## Future Reserved Endpoints

The following endpoints are reserved for later phases and should not be implemented during the MVP unless explicitly requested.

### Async Recognition

```text
POST /api/v1/formulas/tasks
GET /api/v1/formulas/tasks/{task_id}
DELETE /api/v1/formulas/tasks/{task_id}
```

Purpose:

- Support long-running recognition.
- Support queueing.
- Support progress status.
- Support cancellation.

### Batch Recognition

```text
POST /api/v1/formulas/batch-recognize
```

Purpose:

- Recognize multiple formula images in one request.

### Result History

```text
GET /api/v1/formulas/{formula_id}
DELETE /api/v1/formulas/{formula_id}
```

Purpose:

- Retrieve or delete saved recognition results if persistence is introduced later.

### AI Formula Explanation

```text
POST /api/v1/formulas/{formula_id}/explain
POST /api/v1/explanations
```

Purpose:

- Explain recognized formulas.
- Generate variable descriptions.
- Generate step-by-step derivations.

### Technical Document Generation

```text
POST /api/v1/documents
GET /api/v1/documents/{document_id}
```

Purpose:

- Generate Markdown, DOCX, or PDF technical documents from recognized formulas and AI explanations.

### Dedicated Conversion API

```text
POST /api/v1/conversions/latex-to-mathml
```

Purpose:

- Convert user-provided LaTeX into MathML without image recognition.

This is useful later, but the MVP should keep conversion inside `/api/v1/formulas/recognize`.

## MVP API Completion Criteria

The API design stage is complete when:

- The MVP endpoints are documented.
- Request parameters are defined.
- Success and error response structures are defined.
- Upload limits are documented.
- Error codes are documented.
- Future extension endpoints are reserved but not required for MVP implementation.

