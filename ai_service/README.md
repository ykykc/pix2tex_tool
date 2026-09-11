# AI Service Recognition

## Scope and Design

Phase 3.5 adds real single-image recognition to the independent `ai_service/`.
Model lifecycle remains as implemented in Phase 3.3. The current task uses
`POST /recognize` with field `image`, superseding the proposed internal route
for this phase in [the integration design](../docs/pix2tex-integration.md).
Backend is not connected. `inference.py` owns upload parsing, image validation,
preprocessing, model execution and result validation; the route delegates to it.

`ModelManager` provides `load_model()`, `get_model()` and `is_loaded()`.
Loading is synchronous, serialized and idempotent. A fully initialized instance
is published only after success. Access before loading raises an error; failure
leaves the manager unloaded and permits explicit retry. `unload_model()` drops
the manager's reference during shutdown, without guaranteeing immediate memory
release by third-party allocators or other callers.

FastAPI lifespan loads once via a worker thread before accepting requests.
Importing the application does not import Pix2Tex or initialize a model.
Startup failure is logged by cause type and leaves health available with
`model_loaded: false`. There is no automatic retry or Mock fallback.
Each application owns its manager at `app.state.model_manager`; tests inject
factories through `create_app(manager)`.

The default factory imports `pix2tex.cli.LatexOCR` in the active interpreter,
using the validated CPU defaults. Local config, tokenizer, recognition weights
and resizer weights must exist before loading to avoid the checkpoint download
path. This resource layout targets the validated pix2tex 0.1.4 package.
The wrapper restores the root logging level changed during initialization;
other model process side effects remain confined to this independent service.

## Health

`GET /health` returns HTTP 200 for process liveness:

```json
{"status":"ok","model_loaded":true,"model":"pix2tex"}
```

After a loading failure, `model_loaded` is false. A true flag indicates model
initialization, not verified recognition quality. During lifespan loading the
server has not started accepting requests. Startup has no hard timeout in this
phase; a blocked initializer can delay startup. Execution timeouts and readiness
endpoints remain future work. Inference is serialized with a nonblocking lock.

## Recognize

`POST /recognize` accepts `multipart/form-data` containing exactly one file
field named `image`. Swagger describes it as a binary upload. Example from the
repository root, with the service running:

```powershell
curl.exe -X POST http://127.0.0.1:8001/recognize -F "image=@ai_runtime/samples/test_cases/basic/formula_quadratic.png;type=image/png"
```

Success (HTTP 200; formula below is illustrative, not a recorded model result):

```json
{"success":true,"latex":"x^{2}+2x+1=0","model":"pix2tex","processing_time":0.55}
```

Failure:

```json
{"success":false,"error":{"code":"MODEL_UNAVAILABLE","message":"Model is not loaded."}}
```

`processing_time` is measured in seconds, covering multipart parsing, image
decoding/preprocessing and inference in the worker. It excludes request body
reception, thread dispatch, response serialization and startup model loading.

Limits: one PNG/JPEG/WEBP image, maximum file size 5 MiB, total request body at
most 5 MiB plus 64 KiB multipart overhead, width and height each 16 to 4096 pixels.
Declared MIME must match decoded format; animations are rejected. EXIF orientation
is applied, transparency is composited onto white, and input is converted to RGB.
Images are processed in memory; no files are saved. The model's retained
`last_pic` is cleared after inference, including failure paths.

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | BAD_REQUEST | Malformed multipart, multiple fields, or encoded MIME parts |
| 400 | UPLOAD_EMPTY_FILE | Empty image |
| 413 | UPLOAD_FILE_TOO_LARGE | File or total request body limit exceeded |
| 415 | UPLOAD_UNSUPPORTED_TYPE | Wrong request or image MIME type |
| 422 | UPLOAD_FILE_REQUIRED | Missing file in the image field |
| 422 | UPLOAD_INVALID_IMAGE | Corrupt image, MIME mismatch, animation or invalid dimensions |
| 503 | MODEL_UNAVAILABLE | No loaded model; requests do not initialize it |
| 503 | MODEL_BUSY | Another image is currently being processed |
| 500 | RECOGNITION_FAILED | Model exception, non-string or empty output |

The service calls `ModelManager.get_model()` then invokes that same LatexOCR
instance. It never reloads a model per request. Synchronous work runs in a
threadpool while the request waits; this is not a background task or task API.
The lock stays held until execution and cleanup finish. No queue, retry or
hard inference timeout is implemented; a stuck call remains busy. Health can
still respond. Use one service instance and one worker as documented below.

## Dependencies

Phase 3.4 declares the web runtime dependencies in `requirements.txt`:

- `fastapi`: HTTP application framework; supplies Pydantic and Starlette as
  transitive dependencies used by the response schema and lifecycle code.
- `uvicorn`: ASGI server that runs the application.

The file describes the web layer only, not a complete model environment or a
version lock. Pix2Tex, PyTorch, Pillow, model configuration and existing weights
are reused from the validated `ai_runtime/.venv`. They are not copied into
`ai_service/`, and this requirements file does not reinstall or declare them.
pytest and httpx are test dependencies, not included in this runtime file.

The service source lives in `ai_service/`; its interpreter and model dependencies
live in `ai_runtime/.venv`. Backend remains a separate application. Do not use
another environment's site-packages through `sys.path` or copy model files.

The 2026-09-11 environment check found FastAPI, Uvicorn, httpx and Pillow in the
AI environment, but no pytest or python-multipart. This phase installs nothing.
Because FastAPI's standard File/UploadFile parsing needs python-multipart, the
service reads a size-bounded request stream and parses multipart using the
standard-library email BytesParser. It rejects nested/encoded parts and malformed
boundaries. This constrained parser is intended for the single-file local API,
not a general-purpose multipart implementation. Standard FastAPI file parsing
can be reconsidered in a separately authorized dependency task.

## Prepare the Environment

The following is a future setup step: running it will modify the AI virtual
environment by installing web dependencies and any required transitive packages.
It is not necessary for the already prepared current environment and has not
been executed during Phase 3.5. On a fresh environment, from the
repository root, explicitly use the existing AI interpreter:

```powershell
.\ai_runtime\.venv\Scripts\python.exe -m pip install -r ai_service/requirements.txt
.\ai_runtime\.venv\Scripts\python.exe -m pip check
.\ai_runtime\.venv\Scripts\python.exe -B -c "import sys, fastapi, uvicorn; print(sys.executable); print(fastapi.__version__, uvicorn.__version__)"
```

Review dependency conflicts before running the service; an unpinned requirements
file is not a guarantee that every future dependency combination is compatible.
If pip reports unavailable packages, inspect its configured index and
`PIP_NO_INDEX` setting before retrying. This task does not change pip settings.

## Run

After the web dependencies are available, run from the repository root, not
from inside `ai_service/`. Activation is unnecessary with this explicit path:

```powershell
.\ai_runtime\.venv\Scripts\python.exe -B -m uvicorn ai_service.main:app --host 127.0.0.1 --port 8001 --workers 1
```

Alternatively, activate the same environment and run the equivalent command:

```powershell
.\ai_runtime\.venv\Scripts\Activate.ps1
python -B -m uvicorn ai_service.main:app --host 127.0.0.1 --port 8001 --workers 1
```

Use one worker without reload to avoid duplicate model instances. The startup
lifecycle loads the existing local model. If port 8001 is occupied, choose
another port such as 8002 and adjust the health URL. Backend port 8000 is
unaffected. The global Python is not the validated model interpreter.

Once prerequisites are available:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

Expect `status: ok`, `model_loaded: true` and `model: pix2tex` after successful
initialization. A 200 response with `model_loaded: false` means the process is
alive but model loading failed; inspect startup logs and the selected interpreter.
Swagger is at `http://127.0.0.1:8001/docs`. Stop the foreground service with Ctrl+C.

## Validation

With the existing web/test interpreter that contains pytest, from the repository root:

```powershell
& 'D:/py/Python3/python.exe' -B -m pytest ai_service/tests -p no:cacheprovider
```

Tests cover unloaded access, repeated/concurrent loading, failure/retry,
missing dependencies/resources, unload/reload, startup success/failure,
health state, import side effects and recognition success/failure paths.
Default tests use injected models; the real-model test is skipped unless enabled.

Run the recognition tests with actual local weights in the AI environment,
without installing pytest (this test module also supports standard unittest):

```powershell
.\ai_runtime\.venv\Scripts\python.exe -B -c "import os, unittest; os.environ['AI_SERVICE_REAL_MODEL_TEST']='1'; suite=unittest.defaultTestLoader.loadTestsFromName('ai_service.tests.test_recognize'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"
```

The real test uses TestClient with application lifespan, uploads all four PNGs
under `ai_runtime/samples/test_cases`, checks nonempty LaTeX, and verifies model
identity is unchanged. Fixtures are read only. It tests the ASGI endpoint and
actual model, not an external Uvicorn listening socket.

Phase 3.5 validation (2026-09-11): 26 default tests passed, 1 opt-in test skipped;
the AI-environment unittest run passed all 16 tests including real inference.
All four sample uploads returned nonempty LaTeX. Observed worker processing
times were approximately 0.55, 2.81, 0.72 and 0.88 seconds for basic, complex,
engineering and matrix images respectively, excluding model startup.

These are API completion checks, not accuracy guarantees. The basic and voltage
outputs contained incorrect symbols; the multi-line output confused v with nu.
The matrix output retained its structure and elements. Quality improvements,
hard timeouts, Backend integration and any additional APIs remain future work.
PyTorch and Starlette emitted deprecation warnings during validation; no package
versions were changed to address them.
