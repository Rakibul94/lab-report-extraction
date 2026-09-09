
from __future__ import annotations

import json
import logging
from pathlib import Path

from services.ocr_port import OCRLine, OCRPermanentError, OCRProvider, OCRResult

logger = logging.getLogger(__name__)


class MockOCRProvider(OCRProvider):

    """Replays recorded neutral-format provider responses.

    Recording selection: if "<stem>.json" matches the uploaded filename,
    play that recording; otherwise play the default. The uploaded pixels
    are never read — the filename is the scenario switch used by demos
    and tests.
    """

    def __init__(
        self, recordings_dir: str | Path, default_recording: str = "report_001.json"
    ) -> None:
        self.recordings_dir = Path(recordings_dir)
        self.default_recording = self.recordings_dir / default_recording

    def extract(self, image_bytes: bytes, *, filename: str = "") -> OCRResult:
        stem = Path(filename).stem or "default"
        recording_path = self._select_recording(stem)
        logger.info("MOCK OCR: %s -> %s (pixels ignored)", filename, recording_path.name)
        return self._load(recording_path)

    def _select_recording(self, stem: str) -> Path:
        candidate = self.recordings_dir / f"{stem}.json"
        return candidate if candidate.is_file() else self.default_recording

    def _load(self, recording_path: Path) -> OCRResult:
        try:
            with (open(recording_path, encoding="utf-8") as file,):
                recording = json.load(file)
            return OCRResult(
                lines=tuple(
                    OCRLine(text=entry["text"], confidence=float(entry["confidence"]))
                    for entry in recording["lines"]
                )
            )
        except (OSError, KeyError, TypeError, ValueError) as error:
            raise OCRPermanentError(
                f"Malformed recording: {recording_path} ({error})"
            ) from error