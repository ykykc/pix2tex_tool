# Standalone Pix2Tex Test

## Purpose and Boundary

`run_pix2tex_once.py` validates the standalone flow:

```text
formula image -> Pix2Tex LatexOCR -> LaTeX on stdout
```

It accepts one image path, decodes the image with Pillow, loads one model,
and performs one recognition. Relative paths are resolved from the current
working directory before model initialization. Images are closed after use.
This script does not import backend modules or expose an API.

## Environment

Use the existing `ai_runtime/.venv` (Python 3.11.6 in the current environment),
with Pillow, Pix2Tex and its dependencies already installed and validated.
The installed `LatexOCR()` defaults to CPU execution. Model loading happens
on every invocation, so the first result includes initialization time.
Pix2Tex manages its own weights and may download missing checkpoints on
initialization; the current environment already contains the recognition
and image-resizer checkpoints. This script does not install dependencies
or change third-party source code.

## Usage

From the repository root, in PowerShell:

```powershell
cd ai_runtime
.\.venv\Scripts\Activate.ps1
python scripts/run_pix2tex_once.py samples/images/test.png
```

Activation is optional when calling the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe scripts/run_pix2tex_once.py samples/images/test.png
```

An absolute image path is also accepted. Quote paths containing spaces.
Use `--help` to display arguments.

On success, stdout contains the recognized LaTeX string. Library diagnostics
and failure messages go to stderr. Exit codes are `0` for success, `1` for
image/dependency/model/inference failures or empty output, and `2` for invalid
command-line arguments. Inspect the result against the input formula; successful
execution alone does not establish recognition accuracy.

## Tests

From `ai_runtime`, run the focused tests using the standard library:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

These tests use actual Pillow images and a mocked model to cover CLI output,
invalid input, loading/inference failures and empty results without downloading
weights. Run the sample command above separately to verify real model inference.
