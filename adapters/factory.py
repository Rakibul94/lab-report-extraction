
from __future__ import annotations

from services.config import Settings
from services.ocr_port import OCRProvider

from adapters.mock_ocr import MockOCRProvider
from adapters.real_ocr import RealOCRProvider

def create_ocr_provider(settings: Settings) -> OCRProvider:
    if settings.provider == "mock":
        return MockOCRProvider(settings.recordings_dir, default_recording=settings.default_recording)
    raise ValueError(f"Unknown provider: {settings.provider!r}")