# Simple quadratic equation

## Original LaTeX

```latex
x^{2}+2x+1=0
```

## Expected output

```latex
x^{2}+2x+1=0
```

## Test notes

- Input: `formula_quadratic.png`, a synthetic black-on-white formula image.
- Check superscript placement, both plus signs, coefficients and the equals sign.
- Whitespace and optional braces around a single superscript may differ.
- Expected output is a reference, not a recorded Pix2Tex result. Recognition has not been run for this fixture.
- From `ai_runtime`, using the existing virtual environment:

```powershell
python scripts/run_pix2tex_once.py samples/test_cases/basic/formula_quadratic.png
```
