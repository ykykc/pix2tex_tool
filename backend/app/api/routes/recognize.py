from fastapi import APIRouter, File, UploadFile

from app.schemas.recognition import RecognitionResponse
from app.services.recognition_service import recognition_service


router = APIRouter(tags=["recognition"])


@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_formula(file: UploadFile = File(...)) -> RecognitionResponse:
    return await recognition_service.recognize(file)

