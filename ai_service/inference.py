"""Bounded multipart decoding and serialized inference using the loaded model."""

from email import policy
from email.parser import BytesParser
from io import BytesIO
from threading import Lock
import time
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from ai_service.model_manager import ModelManager


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = MAX_IMAGE_BYTES + 64 * 1024
FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}


class InferenceError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def parse_upload(body: bytes, content_type: str):
    if len(body) > MAX_BODY_BYTES:
        raise InferenceError("UPLOAD_FILE_TOO_LARGE", "Request exceeds the upload limit.", 413)
    if "\r" in content_type or "\n" in content_type:
        raise InferenceError("BAD_REQUEST", "Invalid Content-Type header.", 400)
    try:
        header = content_type.encode("ascii")
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + header + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
        )
    except (ValueError, UnicodeError) as exc:
        raise InferenceError("BAD_REQUEST", "Invalid multipart request.", 400) from exc
    if message.get_content_type() != "multipart/form-data":
        raise InferenceError("UPLOAD_UNSUPPORTED_TYPE", "Use multipart/form-data.", 415)
    if not message.is_multipart() or any(part.defects for part in message.walk()):
        raise InferenceError("BAD_REQUEST", "Malformed multipart body or boundary.", 400)
    parts = list(message.iter_parts())
    if len(parts) != 1:
        raise InferenceError("BAD_REQUEST", "Upload exactly one image field.", 400)
    part = parts[0]
    if (part.get_content_disposition() != "form-data"
            or part.get_param("name", header="content-disposition") != "image"
            or part.get_filename() is None or part.is_multipart()):
        raise InferenceError("UPLOAD_FILE_REQUIRED", "Provide a file in the image field.", 422)
    # HTTP uploads carry raw bytes; do not silently decode email encodings.
    if part.get("Content-Transfer-Encoding") is not None:
        raise InferenceError("BAD_REQUEST", "Encoded multipart parts are not supported.", 400)
    contents = part.get_payload(decode=True)
    if not contents:
        raise InferenceError("UPLOAD_EMPTY_FILE", "Image file is empty.", 400)
    if len(contents) > MAX_IMAGE_BYTES:
        raise InferenceError("UPLOAD_FILE_TOO_LARGE", "Image exceeds 5 MiB.", 413)
    mime = part.get_content_type()
    if mime not in FORMATS:
        raise InferenceError("UPLOAD_UNSUPPORTED_TYPE", "Use PNG, JPEG or WEBP images.", 415)
    return contents, mime


def decode_image(contents: bytes, mime: str):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(contents)) as source:
                if source.format != FORMATS[mime] or getattr(source, "n_frames", 1) != 1:
                    raise InferenceError("UPLOAD_INVALID_IMAGE", "Image format mismatch or animation.", 422)
                if not all(16 <= dimension <= 4096 for dimension in source.size):
                    raise InferenceError("UPLOAD_INVALID_IMAGE", "Image dimensions must be 16 to 4096 pixels.", 422)
                source.load()
                with ImageOps.exif_transpose(source) as oriented:
                    with oriented.convert("RGBA") as rgba:
                        with Image.new("RGBA", rgba.size, "white") as background:
                            background.alpha_composite(rgba)
                            return background.convert("RGB")
    except InferenceError:
        raise
    except (UnidentifiedImageError, OSError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise InferenceError("UPLOAD_INVALID_IMAGE", "Cannot decode the image.", 422) from exc


class InferenceService:
    def __init__(self, manager: ModelManager) -> None:
        self.manager = manager
        self._lock = Lock()

    def recognize(self, body: bytes, content_type: str):
        started = time.perf_counter()
        if not self._lock.acquire(blocking=False):
            raise InferenceError("MODEL_BUSY", "Model is processing another image.", 503)
        try:
            contents, mime = parse_upload(body, content_type)
            with decode_image(contents, mime) as image:
                if not self.manager.is_loaded():
                    raise InferenceError("MODEL_UNAVAILABLE", "Model is not loaded.", 503)
                model = self.manager.get_model()
                try:
                    latex = model(image)
                    if not isinstance(latex, str) or not latex.strip():
                        raise ValueError("Empty model result")
                except Exception as exc:
                    raise InferenceError("RECOGNITION_FAILED", "Formula recognition failed.", 500) from exc
                finally:
                    # LatexOCR retains the last image; do not retain user uploads.
                    if hasattr(model, "last_pic"):
                        retained = model.last_pic
                        model.last_pic = None
                        if isinstance(retained, Image.Image):
                            retained.close()
            return {
                "success": True, "latex": latex.strip(), "model": "pix2tex",
                "processing_time": round(time.perf_counter() - started, 4),
            }
        finally:
            self._lock.release()
