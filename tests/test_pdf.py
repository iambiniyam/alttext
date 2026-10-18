from pathlib import Path

import pikepdf
from pikepdf import Array, Dictionary, Name, String

from alttext.scanner import scan_path


def tagged(path: Path, alt: str | None) -> Path:
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    figure = pdf.make_indirect(
        Dictionary(
            Type=Name("/StructElem"),
            S=Name("/Figure"),
            **({"Alt": String(alt)} if alt is not None else {}),
        )
    )
    root = pdf.make_indirect(
        Dictionary(Type=Name("/StructTreeRoot"), K=Array([figure]))
    )
    pdf.Root.StructTreeRoot = root
    pdf.save(path)
    return path


def test_tagged_pdf_present_and_missing(tmp_path):
    present = scan_path(tagged(tmp_path / "present.pdf", "A chart"))
    assert present.items[0].kind == "pdf"
    assert present.items[0].status == "present"

    missing = scan_path(tagged(tmp_path / "missing.pdf", None))
    assert missing.items[0].status == "missing"


def test_untagged_pdf_warns(tmp_path):
    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    source = tmp_path / "untagged.pdf"
    pdf.save(source)
    result = scan_path(source)
    assert result.items == []
    assert "tagged" in result.warnings[0]
