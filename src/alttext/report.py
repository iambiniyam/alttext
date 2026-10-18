"""Report and HTML patch output."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bs4 import BeautifulSoup

from .generator import AltSuggestion
from .scanner import AltItem


def rows(items: list[AltItem], suggestions: list[AltSuggestion | None]) -> list[dict[str, object]]:
    output = []
    for item, suggestion in zip(items, suggestions):
        output.append(
            {
                **item.to_dict(),
                "suggested_alt": suggestion.alt if suggestion else "",
                "decorative": suggestion.decorative if suggestion else False,
                "text_in_image": suggestion.text_in_image if suggestion else "",
                "confidence": suggestion.confidence if suggestion else 0.0,
                "notes": suggestion.notes if suggestion else "",
            }
        )
    return output


def write_json(path: Path | str, payload: dict[str, object]) -> Path:
    path = Path(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_csv(path: Path | str, records: list[dict[str, object]]) -> Path:
    path = Path(path)
    columns = list(records[0].keys()) if records else ["ref", "status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    return path


def write_markdown(path: Path | str, records: list[dict[str, object]]) -> Path:
    path = Path(path)
    lines = ["# Alt text report", "", f"{len(records)} images checked.", ""]
    for record in records:
        lines.append(f"## {record['ref']}")
        lines.append("")
        lines.append(f"- Status: {record['status']}")
        lines.append(f"- Current: {record['current_alt'] or 'none'}")
        lines.append(f"- Suggested: {record['suggested_alt'] or 'none'}")
        if record.get("text_in_image"):
            lines.append(f"- Text in image: {record['text_in_image']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def apply_html(report_path: Path | str, html_path: Path | str, output: Path | str) -> Path:
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    by_ref = {
        str(row["ref"]): str(row["suggested_alt"])
        for row in report.get("items", [])
        if row.get("suggested_alt")
    }
    soup = BeautifulSoup(Path(html_path).read_text(encoding="utf-8"), "html.parser")
    changed = 0
    for image in soup.find_all("img"):
        ref = (image.get("src") or "").strip()
        if ref in by_ref:
            image["alt"] = by_ref[ref]
            changed += 1
    output_path = Path(output)
    output_path.write_text(str(soup), encoding="utf-8")
    return output_path
