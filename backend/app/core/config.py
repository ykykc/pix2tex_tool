from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Latex Web Tool API"
    app_version: str = "0.1.0"
    service_name: str = "latex-web-tool-api"
    api_prefix: str = "/api/v1"
    pix2tex_service_url: str = field(default_factory=lambda: os.environ.get(
        "PIX2TEX_SERVICE_URL", "http://127.0.0.1:8001"
    ))
    max_upload_size_bytes: int = 5 * 1024 * 1024
    supported_image_content_types: tuple = (
        "image/png",
        "image/jpeg",
        "image/webp",
    )


settings = Settings()
