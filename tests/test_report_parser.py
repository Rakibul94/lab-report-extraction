
from services.ocr_port import OCRLine, OCRResult
from services.report_parser import ReportParser

def ocr(*lines: str) -> OCRResult:
    return OCRResult(lines=tuple(OCRLine(text=t, confidence=0.9) for t in lines))


ROW = "Haemoglobin          13.5         gm/dl         13.0 - 17.0"


def test_raw_line_is_verbatim_with_all_whitespace():
    row = ReportParser().parse(ocr(ROW)).results[0]
    assert row.raw_line == ROW              # multi-space columns preserved byte-for-byte


def test_text_result_without_number_is_not_a_result():
    parsed = ReportParser().parse(ocr("Urine Culture : No growth after 48 hrs incubation"))
    assert parsed.results == ()
    assert "Urine Culture" in parsed.unparsed[0]


def test_multiplier_stays_in_unit_no_arithmetic():
    parsed = ReportParser().parse(ocr("Platelet Count       1.2 x 10^3/µL     150 - 450   LOW"))
    row = parsed.results[0]
    assert row.value.low == 1.2             # NOT 1200 - the 10^3 belongs to the unit
    assert row.unit is not None and "10^3" in row.unit.canonical


def test_bilingual_meta_canonicalises():
    parsed = ReportParser().parse(ocr(
        "রোগীর নাম : মোঃ রফিকুল ইসলাম",
        "বয়স : ৩৪ বছর   লিঙ্গ : পুরুষ",
        "রিপোর্টের তারিখ : ১৫/০৩/২০২৪",
    ))
    assert parsed.meta.patient_name == "মোঃ রফিকুল ইসলাম"
    assert parsed.meta.age == "34Y"
    assert parsed.meta.sex == "M"
    assert parsed.meta.report_date == "2024-03-15"