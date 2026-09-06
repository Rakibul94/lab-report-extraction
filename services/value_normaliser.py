
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Value:
    low: float
    high: float | None = None      # None = point value; set = interval
    operator: str = ""             # "", "<", ">"
    raw: str = ""

    @property
    def primary(self) -> float:    # the single number the API promises
        return self.low


@dataclass(frozen=True)
class Unit:
    canonical: str
    raw: str


@dataclass(frozen=True)
class Range:
    low: float | None = None
    high: float | None = None
    operator: str = ""
    raw: str = ""


_NUMBER = r"\d[\d,]*(?:\.\d+)?"

_POINT_RE      = re.compile(rf"^(?P<op>[<>])\s*(?P<num>{_NUMBER})$")
_MULT_RE       = re.compile(rf"^(?P<num>{_NUMBER})\s*[x×]\s*10\s*\^?(?P<exp>\d+)$")
MULT_UNIT_RE  = re.compile(rf"^(?P<num>{_NUMBER})\s*[x×]\s*(?P<unit>10\s*\^?\s*\d+\s*/\s*\S+)$")
_INTERVAL_RE   = re.compile(rf"^(?P<lo>{_NUMBER})\s*-\s*(?P<hi>{_NUMBER})$")
_OPEN_HIGH_RE  = re.compile(rf"^(?P<lo>{_NUMBER})\s*-$")
_OPEN_LOW_RE   = re.compile(rf"^-\s*(?P<hi>{_NUMBER})$")


_BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

def to_float(text: str) -> float | None:
    """'12,500' -> 12500.0 ; '0.8' -> 0.8 ; '12/03' -> None (not a plain number)."""
    text = text.strip().translate(_BANGLA_DIGITS)
    if not re.fullmatch(rf"[<>]?\s*{_NUMBER}", text):
        return None
    return float(text.replace("<", "").replace(">", "").replace(",", "").strip())


def parse_value(text: str) -> Value | None:
    text = text.strip()
    if m := _POINT_RE.fullmatch(text):
        return Value(low=to_float(m["num"]) or 0.0, operator=m["op"], raw=text)
    if m := _INTERVAL_RE.fullmatch(text):
        return Value(low=to_float(m["lo"]) or 0.0, high=to_float(m["hi"]), raw=text)
    if m := _MULT_RE.fullmatch(text):
        return Value(low=(to_float(m["num"]) or 0.0) * 10 ** int(m["exp"]), raw=text)
    if to_float(text) is not None:
        return Value(low=to_float(text) or 0.0, raw=text)
    return None


def parse_range(text: str) -> Range | None:
    text = text.strip()
    if m := _POINT_RE.fullmatch(text):
        return Range(low=to_float(m["num"]), operator=m["op"], raw=text)
    if m := _INTERVAL_RE.fullmatch(text):
        return Range(low=to_float(m["lo"]), high=to_float(m["hi"]), raw=text)
    if m := _OPEN_HIGH_RE.fullmatch(text):
        return Range(low=to_float(m["lo"]), raw=text)
    if m := _OPEN_LOW_RE.fullmatch(text):
        return Range(high=to_float(m["hi"]), raw=text)
    return None


_UNIT_SYNONYMS = {
    "gm/dl": "g/dL", "g/dl": "g/dL", "gm/dl.": "g/dL", "g/dl.": "g/dL",
    "mg/dl": "mg/dL", "mg/dl.": "mg/dL",
    "/cumm": "/µL", "cumm": "/µL",
    "ul": "µL", "pl": "µL",              # 'pL' is OCR for 'µL' (report_002)
    "mill/mm3": "10^6/µL",               # definitional synonym, not algebra
    "ng/ml": "ng/mL",
    "uiu/ml": "µIU/mL",
}


def parse_unit(text: str) -> Unit:
    text = text.strip().rstrip(".")
    return Unit(canonical=_UNIT_SYNONYMS.get(text.lower(), text), raw=text)


_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}

_ISO_RE   = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_SLASH_RE = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")
_TEXT_RE  = re.compile(r"^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})$")


def parse_date(text: str) -> str | None:
    """Canonical YYYY-MM-DD. Ambiguous D/M vs M/D returns None (caller keeps raw)."""
    text = text.strip().translate(_BANGLA_DIGITS)
    if m := _ISO_RE.fullmatch(text):
        return text
    if m := _SLASH_RE.fullmatch(text):
        a, b, year = int(m[1]), int(m[2]), m[3]
        if a > 12 and b <= 12:                       # only DD/MM can produce 13..31 first
            return f"{year}-{b:02d}-{a:02d}"
        if b > 12 and a <= 12:                       # only MM/DD can produce 13..31 second
            return f"{year}-{a:02d}-{b:02d}"
        return None                                  # genuinely ambiguous -> never guess
    if m := _TEXT_RE.fullmatch(text):
        if (month := _MONTHS.get(m[2][:3].lower())) is not None:
            return f"{m[3]}-{month:02d}-{int(m[1]):02d}"
    return None