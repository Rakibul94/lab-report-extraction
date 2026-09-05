
from __future__ import annotations

import logging
from pathlib import Path

from services.document_classifier import looks_like_lab_report
from services.report_parser import Meta, ReportParser, ResultRow
from services.ocr_port import OCRProvider, OCRResult


from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionOutcome:
    """The service layer's complete answer for one document.

    This is the contract the api layer translates to JSON. It contains
    no HTTP vocabulary on purpose — requirement #10.
    """
     
    is_lab_report: bool
    meta: Meta
    results: tuple[ResultRow, ...]
    unparsed: tuple[str, ...]


class LabReportService:
    """Orchestrates the pipeline: OCR -> classify -> parse.

    Ordering rule: the classifier runs BEFORE the parser. A receipt line
    like 'Latte 4.50' is indistinguishable from a test row by grammar
    alone, so grammar must only ever run on documents that already
    look like lab reports.
    """

    def __init__(self, ocr_provider: OCRProvider, parser: ReportParser | None = None,) -> None:
        self.ocr_provider = ocr_provider
        self.parser = parser or ReportParser()

    def extract_report(self, image_bytes: bytes, filename: str = "") -> ExtractionOutcome:
        ocr = self.ocr_provider.extract(image_bytes, filename=filename)
        logger.info(
            "OCR complete: %d lines, mean confidence %.2f",
            len(ocr.lines),
            ocr.mean_confidence,
        )

        if not looks_like_lab_report(ocr):
            logger.info("Classifier rejected document — degrading gracefully")
            return ExtractionOutcome(
                is_lab_report=False,
                unparsed=tuple(line.text for line in ocr.lines),
            )

        parsed = self.parser.parse(ocr)
        logger.info("Parsed %d result rows, %d unparsed lines",
            len(parsed.results),
            len(parsed.unparsed),
        )

        return ExtractionOutcome(
            is_lab_report=True,
            meta=parsed.meta,
            results=parsed.results,
            unparsed=parsed.unparsed,
        )

    
