
from __future__ import annotations

from services.config import Settings
from services.ocr_port import OCRProvider

from adapters.mock_ocr import MockOCRProvider
from adapters.easy_ocr import EasyOCRProvider

def create_ocr_provider(settings: Settings) -> OCRProvider:
    if settings.provider == "mock":
        return MockOCRProvider(settings.recordings_dir, default_recording=settings.default_recording)

    if settings.provider == "easyocr":
        from adapters.easy_ocr import EasyOCRProvider
        return EasyOCRProvider(
            languages=[lang.strip() for lang in settings.easyocr_langs.split(",") if lang.strip()],
            gpu=settings.easyocr_gpu,
            model_dir=settings.easyocr_model_dir,
            download_enabled=settings.easyocr_download,
            max_side=settings.easyocr_max_side,
        )

    
    raise ValueError(f"Unknown provider: {settings.provider!r}")