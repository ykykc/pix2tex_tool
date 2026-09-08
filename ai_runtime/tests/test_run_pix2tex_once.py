"""Focused CLI tests without loading model weights."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_pix2tex_once.py"
SPEC = importlib.util.spec_from_file_location("run_pix2tex_once", SCRIPT)
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)


class RecognitionScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "formula image.png"
        with Image.new("RGB", (32, 16), "white") as image:
            image.save(self.path)
        self.model = Mock(return_value=r"x^{2}")
        self.factory = Mock(return_value=self.model)
        package = types.ModuleType("pix2tex")
        cli = types.ModuleType("pix2tex.cli")
        cli.LatexOCR = self.factory
        patcher = patch.dict("sys.modules", {"pix2tex": package, "pix2tex.cli": cli})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_cli(self, path):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = script.main([str(path)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_success_and_library_output(self):
        def infer(image):
            self.assertEqual(image.size, (32, 16))
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
            print("model diagnostic")
            return r"x^{2}"

        self.model.side_effect = infer
        code, stdout, stderr = self.run_cli(self.path)
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "x^{2}\n")
        self.assertIn("model diagnostic", stderr)
        self.factory.assert_called_once_with()

    def test_missing_file(self):
        code, stdout, stderr = self.run_cli(self.path.with_name("missing.png"))
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Image file not found", stderr)
        self.factory.assert_not_called()

    def test_invalid_image(self):
        invalid = Path(self.temp.name) / "invalid.png"
        invalid.write_bytes(b"not an image")
        code, _, stderr = self.run_cli(invalid)
        self.assertEqual(code, 1)
        self.assertIn("Recognition failed", stderr)
        self.factory.assert_not_called()

    def test_model_loading_failure(self):
        self.factory.side_effect = RuntimeError("load failed")
        code, stdout, stderr = self.run_cli(self.path)
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("load failed", stderr)

    def test_inference_failure(self):
        self.model.side_effect = RuntimeError("inference failed")
        code, _, stderr = self.run_cli(self.path)
        self.assertEqual(code, 1)
        self.assertIn("inference failed", stderr)

    def test_empty_or_invalid_output(self):
        for result in ("", "  ", None):
            with self.subTest(result=result):
                self.model.return_value = result
                code, stdout, stderr = self.run_cli(self.path)
                self.assertEqual(code, 1)
                self.assertEqual(stdout, "")
                self.assertIn("empty or invalid", stderr)

    def test_missing_argument(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            script.main([])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
