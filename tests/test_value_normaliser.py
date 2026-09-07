
import pytest

from services.value_normaliser import parse_date, parse_unit, parse_value


@pytest.mark.parametrize(("raw", "expected_low", "operator"), [
    ("12.5", 12.5, ""),                     # plain
    ("<0.5", 0.5, "<"),                     # operator preserved
    ("12,500", 12500.0, ""),                # thousands separator
    ("1.2 x 10^3", 1200.0, ""),             # bare multiplier -> arithmetic
    ("0.8 - 1.2", 0.8, ""),                 # interval -> low bound
    ("১১.২", 11.2, ""),                     # Bangla digits transliterated
])
def test_parse_value(raw, expected_low, operator):
    v = parse_value(raw)
    assert v is not None and v.low == expected_low and v.operator == operator


def test_interval_keeps_high_bound():
    v = parse_value("0.8 - 1.2")
    assert v.high == 1.2                     # the bound the API drops is still known


def test_non_numbers_are_rejected_not_guessed():
    assert parse_value("14/03/2024") is None
    assert parse_value("08:40") is None


@pytest.mark.parametrize(("raw", "canonical"), [
    ("gm/dl", "g/dL"), ("mg/dL.", "mg/dL"), ("/cumm", "/µL"),
    ("pL", "µL"),                            # OCR misread of µ
    ("Sq/L", "Sq/L"),                        # unknown unit passes through, never converted
])
def test_parse_unit_folds_synonyms_only(raw, canonical):
    assert parse_unit(raw).canonical == canonical


@pytest.mark.parametrize(("raw", "expected"), [
    ("15/03/2024", "2024-03-15"),            # 15>12: only DD/MM possible
    ("2024-03-15", "2024-03-15"),            # ISO
    ("১৫/০৩/২০২৪", "2024-03-15"),           # Bangla digits
    ("03/04/2024", None),                    # ambiguous -> never guessed
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected