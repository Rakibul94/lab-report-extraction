
Fastapi App that performs OCR on lab reports of both english and bangla written text and extracts it into structure JSON meta data like patien name,age etc and test values with units,ranges and flags.

testdata repository contains actual lab reports photos from different hospitals.

How to run:

bash:

git clone https://github.com/Rakibul94/lab-report-extraction.git

pip install -e ".[dev]"

uvicorn main:app --reload

Running test:

pytest -v


## Architecture

The project uses a **ports and adapters** (hexagonal) layout. The idea: the
business logic depends on an *interface* for OCR, never on a concrete engine.
Three layers, each only knows the layer beneath it:

- **`api/` — the HTTP boundary.** `routes.py` validates the upload
  (empty → 400, >10 MB → 413), calls the service, and translates its outcome
  and errors into HTTP responses (OCR failure types map to 502/504).
  `schemas.py` defines the response models. This layer contains no logic.
- **`services/` — the core (pure Python, no OCR imports).**
  - `ocr_port.py` — the contract: an abstract `OCRProvider` with one method
    (`extract(image_bytes) -> OCRResult`) plus its data types and the two
    failure classes (`OCRTemporaryError` = retryable → 504,
    `OCRPermanentError` = not retryable → 502).
  - `lab_report_service.py` — orchestrates the pipeline below.
  - `document_classifier.py` — decides if the OCR text is a lab report at all.
  - `report_parser.py` — extracts header meta and test rows line by line.
  - `value_normaliser.py` — value/unit/range/date normalisation rules.
- **`adapters/` — the outside world.** `mock_ocr.py` (replays recordings),
  `easy_ocr.py` (the real engine; the only file that imports `easyocr`,
  lazily at construction), `box_grouping.py` (converts EasyOCR's scattered
  boxes into reading-order lines), and `factory.py` which reads `LAB_PROVIDER`
  and returns the chosen implementation.

`main.py` is the composition root: it loads settings, asks the factory for a
provider, and injects it into the service. It is the only file that knows
about both sides.

### Request pipeline

For each uploaded image, `LabReportService.extract_report` runs:

1. **OCR** — the injected provider transcribes the image into verbatim text
   lines. A blank page or a photo of something else is a *valid* result here.
2. **Classify** — `looks_like_lab_report` counts evidence keywords (English
   and Bangla) and row-shaped lines. Fewer than two of each → respond with
   `is_lab_report: false`, preserving every line verbatim. The classifier
   runs *before* the parser because a receipt row ("Latte 4.50") is
   grammatically identical to a test row — grammar must only run on
   documents that already look like lab reports.
3. **Parse** — each line either fills header metadata (name, age/sex, date,
   reference no), becomes a `ResultRow` (name, value, unit, range, flag), or
   is preserved verbatim in `unparsed`. Nothing is silently dropped.
4. **Normalise** — numbers, units, and dates are canonicalised under strict
   rules: synonym folding for units only (never unit algebra), ambiguous
   dates kept raw rather than guessed, every `raw_line` kept untouched as an
   audit trail.

### Why this design

- **The heavy, unreliable dependency is isolated.** OCR engines are slow,
  weight-heavy, and worth swapping — Tesseract, RapidOCR and EasyOCR were
  evaluated (see `DECISIONS.md`); EasyOCR won on photo robustness and Bangla
  support. Because of the port, that evaluation never touched parsing code.
- **Fast, deterministic tests.** The mock replays recorded outputs, so the
  whole business layer is tested in milliseconds with no models or network —
  `tests/conftest.py` forces the mock regardless of any local `.env`, so CI
  can never accidentally hit the real engine. `tests/test_layering.py`
  enforces the import rules (e.g. `services/` may not import `adapters/`).
- **Safe by default.** No `.env` → mock provider: the service runs with zero
  credentials and zero downloads, which is also what the Docker image relies on.

Normalized value formats:

VALUE    {"low": float, "high": float|null, "operator": ""|"<"|">", "raw": str}
             point value  → high is null
             interval     → both set ("0.8 - 1.2")
             "<0.5"       → low=0.5, operator="<"
UNIT     {"canonical": str, "raw": str}
             case/synonym folding only (gm/dl → g/dL). NEVER unit algebra (no µL→mL maths).
RANGE    {"low": float|null, "high": float|null, "operator": ""|"<"|">", "raw": str}
             "8.0 -" → high null; "< 200" → operator "<"
DATE     canonical "YYYY-MM-DD"; if day/month ambiguous → keep raw verbatim, no guess
NUMBERS  canonical type is float; thousands commas stripped when comma+3 digits
         "1.2 x 10^3" (bare)   → 1200.0        multiplier applied
         "1.2 x 10^3/µL"       → 1.2 + unit "10^3/µL"   exponent belongs to the unit
RULE     anything unparseable → field carries raw only, value null



Limitation: Extraction of Text accuracy is quite poor.Based on the header block and test table on take home task some of the 
extracted text was not placed accordingly to the labels.Some relevent labels went to unparsed section.