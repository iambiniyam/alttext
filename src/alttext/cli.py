"""Command line interface for alttext."""

from __future__ import annotations

from pathlib import Path

import httpx
import typer
from PIL import Image
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import model_dir
from .generator import build_generator
from .remote import scan_url
from .report import apply_html, write_csv, write_json, write_markdown
from .scanner import scan_path

app = typer.Typer(help="Local-first alt text and image accessibility audit.", no_args_is_help=True)
console = Console()


@app.callback(invoke_without_command=True)
def _root(
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show the version and exit."),
) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()



@app.command()
def scan(
    path: Path = typer.Argument(..., exists=True),
    fail_on_missing: bool = typer.Option(
        False, "--fail-on-missing", help="Exit with status 1 when alt text is missing."
    ),
) -> None:
    """List images and alt attributes that need attention."""
    result = scan_path(path)
    counts = result.counts()
    console.print(f"[bold]{sum(counts.values())}[/bold] images · {counts}")
    table = Table("Status", "Reference", "Context")
    for item in result.items:
        table.add_row(item.status, item.ref, item.context[:70])
    console.print(table)
    for warning in result.warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")
    if fail_on_missing and counts.get("missing", 0):
        raise typer.Exit(code=1)


@app.command("scan-url")
def scan_url_command(
    url: str = typer.Argument(..., help="Page to audit, for example https://example.com"),
    fail_on_missing: bool = typer.Option(False, "--fail-on-missing"),
) -> None:
    """Audit the images on a public HTML page without a browser."""
    try:
        result = scan_url(url)
    except (ValueError, httpx.HTTPError) as exc:
        console.print(f"[red]could not scan URL: {exc}[/red]")
        raise typer.Exit(code=2) from exc
    counts = result.counts()
    console.print(f"[bold]{sum(counts.values())}[/bold] images · {counts}")
    table = Table("Status", "Image", "Context")
    for item in result.items:
        table.add_row(item.status, item.ref[:80], item.context[:55])
    console.print(table)
    for warning in result.warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")
    if fail_on_missing and counts.get("missing", 0):
        raise typer.Exit(code=1)


@app.command()
def generate(
    path: Path = typer.Argument(..., exists=True),
    out: Path = typer.Option(Path("alttext-report.json"), "--out", "-o"),
    model: str = typer.Option("auto", "--model", help="auto, qwen, or heuristic"),
    html: Path | None = typer.Option(None, "--html", help="Patch this HTML file with the suggestions."),
    html_out: Path | None = typer.Option(None, "--html-out", help="Where to write the patched HTML."),
    csv_out: Path | None = typer.Option(None, "--csv", help="Also write a CSV report."),
    markdown_out: Path | None = typer.Option(None, "--markdown", help="Also write a Markdown report."),
) -> None:
    """Write alt text for images that are missing it."""
    result = scan_path(path)
    todo = [item for item in result.items if item.status == "missing"]
    generator = build_generator(model)
    records = []
    suggestions = []
    for item in todo:
        image = Image.open(item.source)
        image.load()
        suggestion = generator.suggest(image, context=item.context)
        suggestions.append(suggestion)
        records.append(
            {
                **item.to_dict(),
                "suggested_alt": suggestion.alt,
                "decorative": suggestion.decorative,
                "text_in_image": suggestion.text_in_image,
                "confidence": suggestion.confidence,
                "notes": suggestion.notes,
            }
        )
    payload = {
        "tool": "alttext",
        "model": generator.name,
        "counts": result.counts(),
        "items": records,
        "warnings": result.warnings,
    }
    write_json(out, payload)
    if csv_out:
        write_csv(csv_out, records)
    if markdown_out:
        write_markdown(markdown_out, records)
    console.print(f"wrote {out} with {len(records)} suggestions using {generator.name}")
    if html and html_out:
        apply_html(out, html, html_out)
        console.print(f"patched {html_out}")


@app.command()
def apply(
    report: Path = typer.Argument(..., exists=True),
    html: Path = typer.Argument(..., exists=True),
    out: Path = typer.Option(Path("index.fixed.html"), "--out", "-o"),
) -> None:
    """Apply a JSON report to an HTML file."""
    apply_html(report, html, out)
    console.print(f"wrote {out}")


@app.command()
def serve(port: int = typer.Option(8791, "--port")) -> None:
    """Start the local web UI."""
    import uvicorn

    uvicorn.run("alttext.server:app", host="127.0.0.1", port=port, log_level="warning")


@app.command()
def doctor() -> None:
    """Check the model and runtime."""
    folder = model_dir()
    ready = (folder / "model.safetensors").exists()
    console.print("model: [bold]qwen3-vl-2b-4bit[/bold]")
    console.print(f"path: {folder}")
    console.print(f"weights: {'ready' if ready else 'missing'}")
    if not ready:
        console.print("Run: [bold]python scripts/download_model.py[/bold]")
    console.print("[green]ready[/green]")


if __name__ == "__main__":
    app()
