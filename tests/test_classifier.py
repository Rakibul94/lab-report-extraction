
from services.document_classifier import looks_like_lab_report
from services.ocr_port import OCRLine, OCRResult


def ocr(*lines: str) -> OCRResult:
    return OCRResult(lines=tuple(OCRLine(text=t, confidence=0.9) for t in lines))


def test_receipt_is_rejected_even_with_numeric_rows():
    assert not looks_like_lab_report(ocr(
        "STAR COFFEE CO.", "Receipt #0043", "Latte 4.50", "Cappuccino 4.50", "TOTAL 16.57",
    ))


def test_report_header_is_accepted():
    assert looks_like_lab_report(ocr(
        "CITY DIAGNOSTIC LABORATORY", "Name : John Doe", "Age : 34 Years",
        "Haemoglobin 13.5 gm/dl 13.0 - 17.0",
        "WBC Count 12,500 /cumm 4,000 - 11,000 HIGH",
    ))

def test_blank_image_is_rejected():
   assert not looks_like_lab_report(OCRResult(lines=()))

def test_prescription_is_rejected_even_with_header_words():
    # evidence >= 2 (patient, age) but rowish == 0 - no numeric table rows
    assert not looks_like_lab_report(ocr(
        "Patient: John Doe",
        "Age : 34 Years   Sex : Male",
        "Rx: Take one tablet daily after meals",
    ))
