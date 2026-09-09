

from __future__ import annotations

import io
import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from adapters.box_grouping import boxes_to_reading_order
from services.ocr_port import (
    OCRPermanentError,
    OCRProvider,
    OCRResult,
    OCRTemporaryError,
)

logger = logging.getLogger(__name__)


class EasyOCRProvider(OCRProvider):
    "This is the OCR engine is selected for Real OCR"
    """Easy OCR: EasyOCR detection+recognition, CPU-only, bilingual.

    The ONLY file importing easyocr. One detector pass feeds two
    recognisers (en + bn by config). First init downloads ~80 MB of
    recogniser weights unless model_dir already holds them.
    """


    def __init__(
        self,
        languages: list[str],
        gpu: bool = False,
        model_dir: str | Path | None = None,
        download_enabled: bool = True,
        max_side: int = 1280,
    ) -> None:
        import easyocr  # heavy (torch) - reached only when this adapter is selected

        self._reader = easyocr.Reader(
            lang_list=languages,
            gpu=gpu,
            model_storage_directory=str(model_dir) if model_dir else None,
            download_enabled=download_enabled,
            verbose=False,
        )
        self.max_side = max_side
        logger.info("EasyOCR ready: languages=%s gpu=%s", languages, gpu)

    def extract(self, image_bytes: bytes, *, filename: str = "") -> OCRResult:
        image = self._load(image_bytes)
        try:
            raw = self._reader.readtext(image, detail=1, paragraph=False, canvas_size = 2560,
                                         decoder="beamsearch", beamWidth=5, contrast_ths=0.1,                   
                                         adjust_contrast=0.5, add_margin=0.15,)   #Run detector + recognizer
        except (RuntimeError, ValueError) as e:
            raise OCRTemporaryError(f"EasyOCR engine error: {e}") from e
        if not raw:                       # blank image: valid, zero lines
            return OCRResult(lines=())
        return boxes_to_reading_order(raw)

    def _load(self, image_bytes: bytes) -> np.ndarray:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image = ImageOps.exif_transpose(image)   # phone photos: honour rotation metadata
            image = image.convert("RGB")
        except UnidentifiedImageError as e:
            raise OCRPermanentError("Unsupported or corrupt image") from e
        w, h = image.size
        scale = self.max_side / max(w, h)
        if scale < 1.0:
             image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        elif max(w, h) < 1500:                     # small phone photo: upscale
             image = image.resize((int(w * 1.5), int(h * 1.5)), Image.LANCZOS)
        image = ImageOps.autocontrast(image.convert("L"))   # photos: uneven lighting
        return np.array(image)