# Ideal buck converter voltage

## Original LaTeX

```latex
V_{o}=D V_{in}
```

## Expected output

```latex
V_{o}=D V_{in}
```

## Test notes

- Input: `formula_buck_voltage.png`, a synthetic black-on-white formula image.
- Ideal buck converter in steady-state continuous conduction: output voltage equals duty ratio times input voltage.
- Check uppercase V and D, the letter o (not zero), and the complete input subscript in.
- Whitespace and explicit multiplication spacing may differ; subscripts must retain their grouping.
- Expected output is a reference, not a recorded Pix2Tex result. Recognition has not been run for this fixture.
- From `ai_runtime`, using the existing virtual environment:

```powershell
python scripts/run_pix2tex_once.py samples/test_cases/engineering/formula_buck_voltage.png
```
