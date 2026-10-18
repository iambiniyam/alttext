from pathlib import Path

from docx import Document
from PIL import Image

from alttext.scanner import scan_path


def make_docx(path: Path, alt: str | None) -> Path:
    image = path.with_suffix(".png")
    Image.new("RGB", (32, 32), "red").save(image)
    document = Document()
    document.add_picture(str(image))
    if alt is not None:
        document.inline_shapes[0]._inline.docPr.set("descr", alt)
    document.save(path)
    return path


def test_docx_present_and_missing(tmp_path):
    present = scan_path(make_docx(tmp_path / "present.docx", "A red square"))
    assert len(present.items) == 1
    assert present.items[0].kind == "docx"
    assert present.items[0].status == "present"

    missing = scan_path(make_docx(tmp_path / "missing.docx", None))
    assert missing.items[0].status == "missing"
