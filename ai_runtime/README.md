# AI Runtime

## Purpose

This directory is reserved for independent AI inference environment planning and Pix2Tex validation.

It is intentionally separated from the FastAPI backend so Pix2Tex, PyTorch, model weights, and other heavy AI dependencies can be evaluated without changing backend code or affecting the current API implementation.

## Pix2Tex Independent Validation Goal

The first validation target is:

```text
formula image
-> Pix2Tex
-> LaTeX output
```

This stage only verifies whether Pix2Tex can recognize a formula image and produce LaTeX text in the local environment.

This stage does not include:

- FastAPI integration.
- Image upload API changes.
- MathML conversion.
- Frontend preview.
- AI formula explanation.
- Technical document generation.

## Boundary With Backend

The backend currently owns API routing, upload validation, service orchestration, and mock recognition behavior.

This `ai_runtime` directory is for standalone model verification only. It should not be imported by backend modules during the current phase.

Future backend integration should happen through the project-owned recognition adapter:

```text
backend/app/recognition/adapter.py
```

The backend should continue to depend on a stable recognition interface, while Pix2Tex-specific loading, preprocessing, inference, and postprocessing remain hidden behind an adapter boundary.

## Recommended Python Version

Recommended Python versions:

```text
Python 3.10
Python 3.11
```

Reasoning:

- Pix2Tex requires Python 3.7 or newer.
- PyTorch support on Windows is generally smoother with newer Python versions.
- A dedicated Python version keeps model dependencies separate from the current global Python environment.

## Virtual Environment Plan

Recommended virtual environment location:

```text
ai_runtime/.venv/
```

Planned setup command:

```powershell
cd G:\AI测试\GitHub\Latex_Web_Tool\ai_runtime
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

This README only documents the plan. The virtual environment has not been created.

## Planned Dependency Installation

Dependencies should be installed only in a later explicit task.

CPU-first plan:

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install pix2tex
```

GPU plan should be considered only after confirming an NVIDIA CUDA-capable GPU and driver environment.

The current environment assessment did not confirm an available NVIDIA CUDA runtime, so CPU validation should be the first path.

## Future Test Flow

Future Pix2Tex validation should follow these steps.

### Step 1: Environment Check

Check:

- Python version.
- pip version.
- Whether the current shell is using `ai_runtime/.venv`.
- Whether PyTorch is installed.
- Whether CUDA is available.
- Whether Pix2Tex can be imported.

Expected result for CPU validation:

```text
Python: 3.10.x or 3.11.x
PyTorch: installed
CUDA available: false
Pix2Tex: installed
```

### Step 2: Single Image Recognition

Use one local formula image as input.

Planned input location:

```text
ai_runtime/samples/images/formula_sample.png
```

Expected output:

```text
LaTeX formula string
```

### Step 3: Save Recognition Output

Planned output location:

```text
ai_runtime/samples/outputs/formula_sample.txt
```

The output file should contain only the recognized LaTeX text.

### Step 4: Decide Backend Integration Strategy

After standalone validation succeeds, decide in a separate design or implementation task whether the backend should:

- Call Pix2Tex in-process through `backend/app/recognition/adapter.py`.
- Call a separate local AI inference service over HTTP.

The initial MVP should prefer the simplest working approach, then split the AI runtime only if model loading time, dependency conflicts, or resource usage require it.

## Current Status

No virtual environment has been created.

No Python dependencies have been installed from this directory.

No Pix2Tex model files have been downloaded.

No backend code or API behavior has been changed by this directory.

