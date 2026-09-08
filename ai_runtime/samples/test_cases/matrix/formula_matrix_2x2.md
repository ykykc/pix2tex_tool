# Two-by-two matrix

## Original LaTeX

```latex
A=\begin{bmatrix}1&2\\3&4\end{bmatrix}
```

## Expected output

```latex
A=\begin{bmatrix}1&2\\3&4\end{bmatrix}
```

## Test notes

- Input: `formula_matrix_2x2.png`, a synthetic black-on-white formula image.
- Check square brackets, two rows, two columns, and element order.
- An equivalent `\left[\begin{array}{cc}...\end{array}\right]` representation is acceptable.
- Flattened numbers, missing row separators, or transposed elements are failures.
- Matrix recognition is an exploratory capability check, not an assumption of model support.
- Expected output is a reference, not a recorded Pix2Tex result. Recognition has not been run for this fixture.
- From `ai_runtime`, using the existing virtual environment:

```powershell
python scripts/run_pix2tex_once.py samples/test_cases/matrix/formula_matrix_2x2.png
```
