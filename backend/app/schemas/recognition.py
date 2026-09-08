from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class UploadedImageRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class RecognitionData(BaseModel):
    latex: str
    processing_time: float = Field(ge=0)


class ErrorData(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class RecognitionResponse(BaseModel):
    success: bool
    data: Optional[RecognitionData]
    error: Optional[ErrorData]

