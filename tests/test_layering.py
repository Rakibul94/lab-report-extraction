
import re
from pathlib import Path

SDKS = {"pytesseract", "easyocr", "torch", "cv2", "numpy", "PIL", "rapidocr"}
IMPORT = re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.M)


def imports_of(path: Path) -> set[str]:
    return {m.split(".")[0] for m in IMPORT.findall(path.read_text(encoding="utf-8"))}


def py_files(*dirs: str):
    root = Path(__file__).resolve().parent.parent
    for d in dirs:
        yield from (root / d).glob("*.py")


def test_services_import_no_fastapi():
    offenders = {f: imports_of(f) & {"fastapi"} for f in py_files("services")}
    assert not any(offenders.values()), offenders


def test_no_sdk_outside_adapters():
    files = [*py_files("api"), *py_files("services"), (Path(__file__).resolve().parent.parent / "main.py")]
    offenders = {f.name: imports_of(f) & SDKS for f in files}
    assert not any(offenders.values()), offenders