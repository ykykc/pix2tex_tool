import time
from io import BytesIO
from typing import Tuple

from fastapi import UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import ApiError
from app.recognition.adapter import MockRecognitionAdapter
from app.schemas.recognition import RecognitionData, RecognitionResponse, UploadedImageRequest


class RecognitionService:
    def __init__(self, adapter: MockRecognitionAdapter) -> None:
        self.adapter = adapter

    async def recognize(self, file: UploadFile) -> RecognitionResponse:
        started_at = time.perf_counter()
        contents = await file.read()
        image_request = self._validate_upload(file, contents)
        latex = self.adapter.recognize(image_request)
        processing_time = round(time.perf_counter() - started_at, 4)

        return RecognitionResponse(
            success=True,
            data=RecognitionData(latex=latex, processing_time=processing_time),
            error=None,
        )

    def _validate_upload(self, file: UploadFile, contents: bytes) -> UploadedImageRequest:
        content_type = file.content_type or ""
        if content_type not in settings.supported_image_content_types:
            raise ApiError(
                code="UPLOAD_UNSUPPORTED_TYPE",
                message="Uploaded file type is not supported.",
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                details={"supported_content_types": list(settings.supported_image_content_types)},
            )

        size_bytes = len(contents)
        if size_bytes == 0:
            raise ApiError(
                code="UPLOAD_EMPTY_FILE",
                message="Uploaded file is empty.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if size_bytes > settings.max_upload_size_bytes:
            raise ApiError(
                code="UPLOAD_FILE_TOO_LARGE",
                message="Uploaded file exceeds the maximum size of 5 MB.",
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                details={"max_size_bytes": settings.max_upload_size_bytes},
            )

        width, height = self._read_image_size(contents)

        return UploadedImageRequest(
            filename=file.filename or "",
            content_type=content_type,
            size_bytes=size_bytes,
            width=width,
            height=height,
        )

    def _read_image_size(self, contents: bytes) -> Tuple[int, int]:
        try:
            with Image.open(BytesIO(contents)) as image:
                image.verify()
                return image.size
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ApiError(
                code="UPLOAD_INVALID_IMAGE",
                message="Uploaded file cannot be read as a valid image.",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            ) from exc


recognition_service = RecognitionService(adapter=MockRecognitionAdapter())
