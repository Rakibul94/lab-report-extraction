
from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.ocr_port import OCRResult
from services.value_normaliser import (
    Range, Unit, Value, parse_date, parse_range, parse_unit, parse_value, to_float,
)

@dataclass(frozen=True)
class ResultRow:
    test_name: str
    value: Value | None = None
    unit: Unit | None = None
    reference_range: Range | None = None
    date: str | None = None   # "H", "L", "" — canonical
    raw_text: str = ""   #verbatim,never touched


@dataclass
class Meta:
    patient_name: str | None = None
    age: str | None = None
    sex: str | None = None
    report_date: str | None = None
    lab_name: str | None = None
    reference_no: str | None = None
    report_date_raw: str | None = None


@dataclass
class ParsedReport:
    meta: Meta = field(default_factory=Meta)
    results: tuple[ResultRow, ...] = ()
    unparsed: tuple[str, ...] = ()


_FLAG = {"high": "H", "h": "H", "low": "L", "l": "L", "*": "H", "e": "E"}

_LAB_KEYWORDS = re.compile(r"(?i)\b(lab|diagnosti|patholog|clinic|hospital)")

_META_PATTERNS = [
    ("patient_name", re.compile(r"(?i)\bname\s*:?\s*([A-Za-z][A-Za-z .'-]{2,})")),
    ("age_and_sex",  re.compile(r"(?i)\bage\s*:?\s*(\d{1,3})\s*(years?|yrs?|y)?\s*(?:,)?\s*(?:sex\s*:?\s*)?(male|female|m|f)?")),
    ("report_date",  re.compile(r"(?i)\breport(?:ed)?\s+date\s*:?\s*([0-9][0-9./-]{6,10})")),
    ("reference_no", re.compile(r"(?i)\breference\s*(?:no|number|#)\s*:?\s*([A-Za-z0-9/-]+)")),
]

_NOT_RESULT = re.compile(
    r"(?i)^\s*(test\b.*(?:unit|result)|method\b|page\b|end of report|dr\.|\*|~)")
    

class ReportParser:

    def parse(self, ocr: OCRResult) -> ParsedReport:
        report = ParsedReport()
        meta = Meta()
        for line in ocr.lines:
            text = line.text
            self._absorb_meta(meta, text)
            if _NOT_RESULT.match(text):
                continue
            if row := self._try_row(text):
                report.results += (row,)
            else:
                report.unparsed += (text,)
        report.meta = self._finish_meta(meta, ocr)
        return report

    # ---------- header ----------

    def _absorb_meta(self, meta: Meta, text: str) -> None:
        for key, pattern in _META_PATTERNS:
            if getattr(meta, key, None) is None and (m := pattern.search(text)):
                if key == "age_and_sex":
                    meta.age = m[1] + (m[2] or "")[:1].upper() or None
                    if m[3]:
                        meta.sex = {"male": "M", "female": "F", "m": "M", "f": "F"}[m[3].lower()]
                elif key == "report_date":
                    meta.report_date_raw = m[1]
                    meta.report_date = parse_date(m[1])
                else:
                    setattr(meta, key, m[1].strip())

    def _finish_meta(self, meta: Meta, ocr: OCRResult) -> Meta:
        if meta.lab_name is None:
            for line in ocr.lines[:4]:
                if _LAB_KEYWORDS.search(line.text):
                    meta.lab_name = line.text.strip()
                    break
            else:
                meta.lab_name = ocr.lines[0].text.strip() if ocr.lines else None
        return meta

    # ---------- results table ----------

    def _try_row(self, text: str) -> ResultRow | None:
        tokens = text.split()
        flag = ""
        if tokens and tokens[-1].lower() in _FLAG:
            flag = _FLAG[tokens.pop().lower()]

        reference = self._pop_range(tokens)

        value, unit = self._pop_value_and_unit(tokens)
        if value is None:
            return None

        name = " ".join(tokens)
        if len(name) < 3 or not re.search(r"[A-Za-z]{3}", name):
            return None
        return ResultRow(name, value, unit, reference, flag, text)

    def _pop_range(self, tokens: list[str]) -> Range | None:
        # pattern A: 'N - N' possibly followed by a range-unit token ('x10'3/uL')
        for take in (4, 3, 2, 1):
            if len(tokens) < take:
                continue
            candidate = " ".join(tokens[-take:])
            if (r := parse_range(candidate)) is not None:
                del tokens[-take:]
                return Range(r.low, r.high, r.operator, candidate)
            # 'N - N unit': unit glued after the interval belongs to the range, keep in raw
            parts = candidate.split()
            if len(parts) >= 4 and (r := parse_range(" ".join(parts[:-1]))) is not None:
                del tokens[-take:]
                return Range(r.low, r.high, r.operator, candidate)
        return None

    def _pop_value_and_unit(self, tokens: list[str]) -> tuple[Value | None, Unit | None]:
        for take in (4, 3, 2, 1):
            if len(tokens) < take:
                continue
            candidate = " ".join(tokens[-take:])

            if m := _MULT_UNIT_RE.fullmatch(candidate):        # '1.2 x 10^3/µL'
                v = parse_value(m["num"]); u = parse_unit(re.sub(r"\s", "", m["unit"]))
                if v: del tokens[-take:]; return v, u

            parts = candidate.split()
            maybe_value, maybe_unit = parts[0], " ".join(parts[1:])

            if (v := parse_value(" ".join(parts[-2:]))) is not None and len(parts) >= 3 \
                    and _INTERVALish(" ".join(parts[-2:])):     # '0.8 - 1.2 mg/dL'
                del tokens[-take:]; return v, Unit(maybe_unit, maybe_unit) if maybe_unit else None

            if parse_unit(maybe_unit or maybe_value).canonical and (v := parse_value(maybe_value)):
                del tokens[-take:]
                return v, parse_unit(maybe_unit) if maybe_unit else None
        return None, None