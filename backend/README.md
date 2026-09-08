# Backend

FastAPI backend for the Latex Web Tool formula recognition platform.

Current scope:

- FastAPI application entrypoint.
- Configuration module.
- API route structure.
- MVP health endpoint.
- Mock formula recognition endpoint.
- Multipart image upload validation for the mock recognition endpoint.

Not implemented yet:

- Pix2Tex integration.
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
