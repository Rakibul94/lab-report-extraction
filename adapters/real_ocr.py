
from __future__ import annotations

import logging
from pathlib import Path

import pytesseract
from PIL import Image

from services.ocr_port import OCRProvider, OCRLine, OCRResult, OCRProviderError, OCRTemporaryError, OCRPermanentError

logger = logging.getLogger(__name__)

class RealOCRProvider(OCRProvider):

    def extract(self, image_path: Path) -> OCRResult:

        """Tesseract adapter: the ONLY file in the project that imports an OCR SDK."""

    def extract(self, image_path: Path) -> OCRResult:
        logger.info("REAL OCR: extracting %s", image_path)
        try:
            image = Image.open(image_path)
            data = pytesseract.image_to_data(
                image, lang="eng", output_type=pytesseract.Output.DICT
            )
        except pytesseract.TesseractNotFoundError as error:
            raise OCRPermanentError("Tesseract binary is not installed") from error
        except OSError as error:
            raise OCRPermanentError(f"Unreadable image: {image_path}") from error
        except Exception as error:
            raise OCRProviderError("OCR engine failed") from error

        lines: list[OCRLine] = []
        current_key: tuple[int, int, int] | None = None
        words: list[str] = []
        confidences: list[float] = []

        for i in range(len(data["text"])):
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            confidence = float(data["conf"][i])
            text = data["text"][i].strip()

            if key != current_key:
                if words:
                    lines.append(self._build_line(words, confidences))
                current_key = key
                words, confidences = [], []

            if text and confidence >= 0:
                words.append(text)
                confidences.append(confidence / 100.0)

        if words:
            lines.append(self._build_line(words, confidences))

        return OCRResult(lines=tuple(lines))

    @staticmethod
    def _build_line(words: list[str], confidences: list[float]) -> OCRLine:
        return OCRLine(
            text=" ".join(words),
            confidence=sum(confidences) / len(confidences),
        )

        