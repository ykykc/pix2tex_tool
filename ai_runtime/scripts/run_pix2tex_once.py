"""Recognize one local formula image using the independent Pix2Tex runtime."""

import argparse
from contextlib import redirect_stdout
from pathlib import Path
import sys


def recognize_image(image_path: Path) -> str:
    image_path = image_path.expanduser().resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    from PIL import Image

    # Decode before loading the model; keep third-party output off stdout.
    with Image.open(image_path) as image:
        image.load()
        with redirect_stdout(sys.stderr):
            from pix2tex.cli import LatexOCR

            model = LatexOCR()
            latex = model(image)

    if not isinstance(latex, str) or not latex.strip():
        raise ValueError("Pix2Tex returned an empty or invalid LaTeX result")
    return latex.strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_path", type=Path, help="Path to a formula image")
    args = parser.parse_args(argv)

    try:
        latex = recognize_image(args.image_path)
    except Exception as exc:
        print(f"Recognition failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    print(latex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
