
from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.ocr_port import OCRResult
from services.value_normaliser import (
    MULT_UNIT_RE, Range, Unit, Value, parse_date, parse_range, parse_unit, parse_value, to_float,
)

@dataclass(frozen=True)
class ResultRow:
    test_name: str
    value: Value                 # required: every result carries a numeric value
    unit: Unit | None = None
    reference_range: Range | None = None
    flag: str = ""               # "H", "L", "E", ""
    raw_line: str = ""           # verbatim OCR line, never touched


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
    unparsed: tuple[str, ...] = () #Leftover lines that got rejected


_FLAG = {"high": "H", "h": "H", "low": "L", "l": "L", "*": "H", "e": "E"}

_BN = "\u0980-\u09FF"   # the Bangla Unicode block, for readable char classes

_LAB_KEYWORDS = re.compile(
    r"(?i)\b(lab|diagnosti|patholog|clinic|hospital|"
    r"ল্যাব|ডায়াগনস্টিক|প্যাথলজি|ক্লিনিক|হাসপাতাল)")

_META_PATTERNS = [
    ("patient_name",
     re.compile(rf"(?i)\b(?:name|নাম)\s*:?\s*([A-Za-z{_BN}][A-Za-z{_BN} .:'\-]{{2,}})")),
    ("age_and_sex",
     re.compile(rf"(?i)(?:\bage\b|বয়স)\s*:?\s*(\d{{1,3}}|[০-৯]{{1,3}})\s*"
                rf"(?:years?|yrs?|y|বছর)?\s*,?\s*(?:(?:sex\s*:?|লিঙ্গ\s*:?)\s*)?"
                rf"(male|female|m|f|পুরুষ|মহিলা|নারী)?")),
    ("report_date",
     re.compile(r"(?i)(?:report(?:ed)?\s+date|রিপোর্টের\s+তারিখ|তারিখ)\s*:?\s*([0-9০-৯][0-9০-৯./-]{5,10})")),
    ("reference_no",
     re.compile(r"(?i)\b(?:reference\s*(?:no|number|#)|রেফারেন্স\s*(?:নং|নাম্বার)?)\s*:?\s*([A-Za-z0-9/-]+)")),
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
                    unit = "Y" if m[2] else ""           # years/yrs/y/বছর -> one canonical unit
                    meta.age = m[1].translate(_BANGLA_DIGITS) + unit or None
                    if m[3]:
                        meta.sex = {
                            "male": "M", "female": "F", "m": "M", "f": "F",
                            "পুরুষ": "M", "মহিলা": "F", "নারী": "F",
                        }[m[3].lower()]
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
        if len(name) < 3 or not re.search(r"[A-Za-z]{3}", name): # The gate
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

            # '1.2 x 10^3/µL' -> multiplier belongs to the UNIT, no arithmetic
            if m := MULT_UNIT_RE.fullmatch(candidate):
                if v := parse_value(m["num"]):
                    unit = parse_unit(re.sub(r"\s+", "", m["unit"]))
                    del tokens[-take:]
                    return v, unit

            parts = candidate.split()

            # '0.8 - 1.2 mg/dL' -> interval value with unit glued after
            if len(parts) >= 4 and (v := parse_value(" ".join(parts[:-1]))) is not None:
                unit = parse_unit(parts[-1])
                del tokens[-take:]
                return v, unit

            # '13.5 gm/dl' -> point value + unit (guard: unit must NOT be a number)
            if len(parts) >= 2 and (v := parse_value(parts[0])) is not None \
                    and to_float(parts[1]) is None:
                unit = parse_unit(" ".join(parts[1:]))
                del tokens[-take:]
                return v, unit

            # '212' -> bare value
            if (v := parse_value(candidate)) is not None:
                del tokens[-take:]
                return v, None
        return None, None