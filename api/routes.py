
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.schemas import ExtractResponse, MetaOut, ResultOut
from services.config import Settings
from services.lab_report_service import LabReportService
from services.ocr_port import OCRPermanentError, OCRTemporaryError

logger = logging.getLogger(__name__)

router = APIRouter()

def create_router(service: LabReportService, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

    @router.post("/extract", response_model=ExtractResponse)
    async def extract_report(image: Annotated[UploadFile, File()]) -> ExtractResponse:
        data = await image.read()

        if len(data) > settings.max_upload_bytes:
            raise HTTPException(413, "Image too large")
        if not data:
            raise HTTPException(400, "Empty upload")

        try:
            outcome = service.extract_report(data, filename=image.filename or "")
        except OCRPermanentError as e:
            raise HTTPException(502, f"OCR provider failed: {e}") from e
        except OCRTemporaryError as e:
            raise HTTPException(504, f"OCR provider timed out: {e}") from e

        warnings: list[str] = []
        if not outcome.is_lab_report:
            warnings.append("Document does not appear to be a lab report.")
        else:
            warnings.extend(
                f"Unparsed line preserved verbatim: {line!r}"
                for line in outcome.unparsed
            )

        return ExtractResponse(
            meta=MetaOut(
                patient_name=outcome.meta.patient_name,
                age=outcome.meta.age,
                sex=outcome.meta.sex,
                report_date=outcome.meta.report_date or outcome.meta.report_date_raw,
                lab_name=outcome.meta.lab_name,
                reference_no=outcome.meta.reference_no,
            ),
            results=[ResultOut(
                test_name=row.test_name,
                value=row.value.primary,
                operator=row.value.operator,
                unit=row.unit.canonical if row.unit else None,
                reference_range=row.reference_range.raw if row.reference_range else None,
                flag=row.flag,
                raw_line=row.raw_line,
            ) for row in outcome.results],
            is_lab_report=outcome.is_lab_report,
            warnings=warnings,
        )

    return router