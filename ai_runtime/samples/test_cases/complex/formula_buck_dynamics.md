# Multi-line buck converter dynamics

## Original LaTeX

```latex
\begin{aligned}
L\frac{di_L}{dt}&=V_{in}-v_C\\
C\frac{dv_C}{dt}&=i_L-\frac{v_C}{R}\\
E&=\frac{1}{2}Li_L^{2}+\frac{1}{2}Cv_C^{2}
\end{aligned}
```

## Expected output

```latex
\begin{aligned}
L\frac{di_L}{dt}&=V_{in}-v_C\\
C\frac{dv_C}{dt}&=i_L-\frac{v_C}{R}\\
E&=\frac{1}{2}Li_L^{2}+\frac{1}{2}Cv_C^{2}
\end{aligned}
```

## Test notes

- Input: `formula_buck_dynamics.png`, a synthetic black-on-white formula image.
- The first two equations describe an ideal buck converter during its switch-on interval with a resistive load. The third gives stored LC energy.
- Check all three rows, derivative fractions, minus signs, subscripts, superscripts and the two one-half factors.
- Preserve uppercase/lowercase distinctions and the order of every term.
- Equivalent aligned/array environments, whitespace, `\dfrac` versus `\frac`, and harmless grouping differences are acceptable after rendering comparison.
- Dropped rows, flattened fractions, or misplaced exponents are failures. Multi-line recognition is an exploratory capability check.
- Expected output is a reference, not a recorded Pix2Tex result. Recognition has not been run for this fixture.
- From `ai_runtime`, using the existing virtual environment:

```powershell
python scripts/run_pix2tex_once.py samples/test_cases/complex/formula_buck_dynamics.png
```
