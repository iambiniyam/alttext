"""Find images that need alt text in folders, HTML, and Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif"}


@dataclass(slots=True)
class AltItem:
    ref: str
    source: str
    kind: str
    current_alt: str | None
    context: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ref": self.ref,
            "source": self.source,
            "kind": self.kind,
            "current_alt": self.current_alt,
            "context": self.context,
            "status": self.status,
        }


@dataclass(slots=True)
class ScanResult:
    items: list[AltItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item.status] = counts.get(item.status, 0) + 1
        return counts


def _status(alt: str | None) -> str:
    if alt is None:
        return "missing"
    if not alt.strip():
        return "decorative"
    return "present"


def scan_html(path: Path) -> ScanResult:
    result = ScanResult()
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for image in soup.find_all("img"):
        src = (image.get("src") or "").strip()
        if not src:
            continue
        if src.startswith(("http://", "https://", "data:")):
            result.warnings.append(f"skipped remote image: {src}")
            continue
        parent = image.find_parent(["figure", "a", "p", "div"])
        context = " ".join(parent.get_text(" ", strip=True).split())[:240] if parent else ""
        local = (path.parent / src).resolve()
        if not local.exists():
            result.warnings.append(f"missing file: {src}")
        result.items.append(
            AltItem(
                ref=src,
                source=str(local),
                kind="html",
                current_alt=image.get("alt"),
                context=context,
                status=_status(image.get("alt")),
            )
        )
    return result


MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def scan_markdown(path: Path) -> ScanResult:
    result = ScanResult()
    text = path.read_text(encoding="utf-8", errors="replace")
    for match in MARKDOWN_IMAGE.finditer(text):
        alt, src = match.group(1), match.group(2)
        if src.startswith(("http://", "https://", "data:")):
            result.warnings.append(f"skipped remote image: {src}")
            continue
        local = (path.parent / src).resolve()
        if not local.exists():
            result.warnings.append(f"missing file: {src}")
        start = max(0, match.start() - 120)
        context = " ".join(text[start : match.start()].split())[-200:]
        result.items.append(
            AltItem(
                ref=src,
                source=str(local),
                kind="markdown",
                current_alt=alt,
                context=context,
                status=_status(alt),
            )
        )
    return result


def scan_docx(path: Path) -> ScanResult:
    """Audit alt text on images embedded in a DOCX file."""
    from docx import Document

    result = ScanResult()
    document = Document(str(path))
    for index, shape in enumerate(document.inline_shapes, start=1):
        doc_pr = shape._inline.docPr
        alt = doc_pr.get("descr")
        title = doc_pr.get("title")
        result.items.append(
            AltItem(
                ref=f"image {index}",
                source=str(path),
                kind="docx",
                current_alt=alt,
                context=title or path.stem,
                status=_status(alt),
            )
        )
    if not result.items:
        result.warnings.append("no inline images found in the DOCX file")
    return result


def scan_folder(path: Path) -> ScanResult:
    result = ScanResult()
    for file in sorted(path.rglob("*")):
        if file.is_file() and file.suffix.lower() in IMAGE_SUFFIXES:
            result.items.append(
                AltItem(
                    ref=file.name,
                    source=str(file),
                    kind="image",
                    current_alt=None,
                    context=file.stem.replace("_", " ").replace("-", " "),
                    status="missing",
                )
            )
    return result


def scan_path(path: Path | str) -> ScanResult:
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_dir():
        return scan_folder(path)
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return scan_html(path)
    if suffix in {".md", ".markdown"}:
        return scan_markdown(path)
    if suffix == ".docx":
        return scan_docx(path)
    if suffix in IMAGE_SUFFIXES:
        return ScanResult(
            items=[
                AltItem(
                    ref=path.name,
                    source=str(path),
                    kind="image",
                    current_alt=None,
                    context=path.stem.replace("_", " ").replace("-", " "),
                    status="missing",
                )
            ]
        )
    raise ValueError(f"unsupported file: {path}")
