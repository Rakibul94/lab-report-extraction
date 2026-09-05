
from __future__ import annotations

import re

from services.ocr_port import OCRResult

_EVIDENCE = re.compile(
    r"(?i)\b(patient|age\s*:?\s*\d|sex|report date|reference|investigation|"
    r"laborator|diagnosti|patholog|haemoglobin|glucose|cholesterol|creatinine)\b")

_ROWISH = re.compile(r"^[A-Za-z][A-Za-z ()/,%-]*\s+[<>]?\d[\d,.]*")


def looks_like_lab_report(ocr: OCRResult) -> bool:
    evidence = sum(1 for line in ocr.lines if _EVIDENCE.search(line.text))
    rowish = sum(1 for line in ocr.lines if _ROWISH.match(line.text))
    return evidence >= 2 and rowish >= 2
