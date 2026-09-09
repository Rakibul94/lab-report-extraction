
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration. Every field is an env var: LAB_PROVIDER, LAB_RECORDINGS_DIR, ..."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LAB_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "lab-report-extraction"
    provider: Literal["mock", "easyocr"] = "mock"   # default = mock: no creds, no model
    recordings_dir: Path = Path("recordings")
    default_recording: str = "report_001.json"
    max_upload_bytes: int = 10 * 1024 * 1024          # reject >10 MB at the boundary




    # --- easyocr (pip-only; downloads recogniser weights on first start) ---
    easyocr_langs: str = "en"           # comma string, NOT a list - see note
    easyocr_gpu: bool = False
    easyocr_max_side: int = 1280           # EasyOCR's detector is heavy: cap input pixels
    easyocr_model_dir: Path | None = None  # point here + download=false = pre-baked weights
    easyocr_download: bool = True


def get_settings() -> Settings:
    return Settings()