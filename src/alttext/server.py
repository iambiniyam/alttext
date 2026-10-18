"""Local web interface for alttext."""

from __future__ import annotations

import io
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

from .generator import build_generator
from .remote import scan_url
from .scanner import IMAGE_SUFFIXES

STATIC = Path(__file__).resolve().parent / "static"
MAX_UPLOAD = 12 * 1024 * 1024
MAX_FILES = 20
Image.MAX_IMAGE_PIXELS = 40_000_000

app = FastAPI(title="alttext", version="0.1.2")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
generator = build_generator("auto")
lock = threading.Lock()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/healthz")
def health() -> dict[str, object]:
    return {"ok": True, "model": generator.name}


@app.post("/api/scan-url")
async def scan_public_url(url: str = Form(...)) -> JSONResponse:
    """Audit a public HTML page without downloading its images."""
    try:
        result = scan_url(url.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"could not fetch the page: {exc}") from exc
    return JSONResponse(
        {
            "url": url,
            "counts": result.counts(),
            "items": [item.to_dict() for item in result.items],
            "warnings": result.warnings,
        }
    )


@app.post("/api/suggest")
async def suggest(
    files: list[UploadFile] = File(...), context: str = Form("")
) -> JSONResponse:
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"too many images (max {MAX_FILES})")
    output = []
    for upload in files:
        suffix = Path(upload.filename or "image").suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"unsupported image: {upload.filename}")
        payload = await upload.read(MAX_UPLOAD + 1)
        if len(payload) > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail=f"{upload.filename}: image too large (max 12 MB)")
        try:
            image = Image.open(io.BytesIO(payload))
            image = ImageOps.exif_transpose(image)
            image.load()
        except Image.DecompressionBombError as exc:
            raise HTTPException(status_code=413, detail=f"{upload.filename}: too many pixels") from exc
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail=f"{upload.filename}: not a readable image") from exc
        with lock:
            suggestion = generator.suggest(image, context=context)
        output.append({"name": upload.filename, "suggestion": suggestion.to_dict()})
    return JSONResponse({"model": generator.name, "items": output})
