import uuid

from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {
        "success": True,
        "data": {
            "status": "ok",
            "service": settings.service_name,
        },
        "error": None,
        "meta": {
            "request_id": f"req_{uuid.uuid4().hex}",
        },
    }

