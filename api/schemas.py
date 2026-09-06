
from __future__ import annotations

from pydantic import BaseModel, Field

class MetaOut(BaseModel):
    patient_name: str | None = None
    age: str | None = None
    sex: str | None = None
    report_date: str | None = None     # canonical ISO when parsed; raw when ambiguous
    lab_name: str | None = None
    reference_no: str | None = None

class ResultOut(BaseModel):
    test_name: str
    value: float                      # spec: every result carries a numeric value
    operator: str = ""                # extra, documented in README
    unit: str | None = None
    reference_range: str | None = None
    flag: str = ""
    raw_line: str                     # spec: verbatim, never cleaned

class ExtractResponse(BaseModel):
    meta: MetaOut
    results: list[ResultOut]
    is_lab_report: bool = True        # extra; false => graceful 'not a lab report'
    warnings: list[str] = []