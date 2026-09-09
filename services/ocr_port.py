
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class OCRProviderError(Exception):
    """Base class for every OCR provider failure."""


class OCRTemporaryError(OCRProviderError):
    """Retryable failure: timeout, throttling, transient network error."""


class OCRPermanentError(OCRProviderError):
    """Non-retryable failure: bad credentials, corrupt or unsupported image."""


@dataclass(frozen=True)
class OCRLine:
    """One line of OCR output. `text` is verbatim: original casing, spacing,
    punctuation, and OCR mistakes included. It becomes `raw_line` downstream
    and must never be cleaned or rewritten."""

    text: str
    confidence: float  # normalized to 0.0 - 1.0 by the adapter


@dataclass(frozen=True)
class OCRResult:
    """Full-page transcription. A blank image or a photo of a cat is a VALID
    result (possibly zero lines) — deciding whether it is a lab report is the
    service's job, not the provider's."""

    lines: tuple[OCRLine, ...]

    @property
    def full_text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def mean_confidence(self) -> float:
        if not self.lines:
            return 0.0
        return sum(line.confidence for line in self.lines) / len(self.lines)


class OCRProvider(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, *, filename: str = "") -> OCRResult:
        """Transcribe one image into verbatim OCR lines.

        Promises:
        - Line text is returned exactly as the engine produced it.
        - An empty or nonsense result is valid; raise nothing for it.
        - Raises only OCRProviderError subclasses.
        """