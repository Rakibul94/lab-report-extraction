
from tests.conftest import build_client


def extract(client, filename: str, content: bytes = b"fake-pixels"):
    return client.post(
        "/api/v1/documents/extract",
        files={"image": (filename, content, "image/png")},
    )


def test_extract_happy_path_full_shape(client):
    r = extract(client, "report_001.png")
    assert r.status_code == 200
    body = r.json()
    assert set(body["meta"]) >= {
        "patient_name", "age", "sex", "report_date", "lab_name", "reference_no"
    }
    assert body["meta"]["patient_name"] == "John Doe"
    assert body["meta"]["report_date"] == "2024-03-15"
    first = body["results"][0]
    assert set(first) >= {"test_name", "value", "unit", "reference_range", "flag", "raw_line"}
    assert isinstance(first["value"], (int, float)) and not isinstance(first["value"], bool)
    assert any(row["value"] == 12500.0 and row["flag"] == "H" for row in body["results"])  # WBC


def test_receipt_degrades_gracefully_over_http(client):
    r = extract(client, "not_a_lab_report.png")
    assert r.status_code == 200                 # NOT an error - a truthful answer
    body = r.json()
    assert body["is_lab_report"] is False and body["results"] == []
    assert all(field is None for field in body["meta"].values())   # nothing invented
    assert any("does not appear" in w for w in body["warnings"])
    assert any("Latte 4.50" in w for w in body["warnings"])       


def test_empty_upload_rejected(client):
    assert extract(client, "x.png", b"").status_code == 400


def test_oversized_upload_rejected():
    small = build_client(max_upload_bytes=8)
    assert extract(small, "x.png", b"0123456789").status_code == 413


def test_unknown_filename_degrades_to_non_lab_default(client):
    r = extract(client, "IMG_2043.jpg")        # no recordings/IMG_2043.json
    assert r.status_code == 200
    body = r.json()
    assert body["is_lab_report"] is False and body["results"] == []
    assert all(field is None for field in body["meta"].values())