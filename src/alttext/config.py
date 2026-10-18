"""Paths and model settings."""

from __future__ import annotations

import os
from pathlib import Path


def model_dir() -> Path:
    return Path(
        os.getenv(
            "ALTTEXT_MODEL_DIR",
            str(Path.home() / ".alttext" / "models" / "qwen3-vl-2b-4bit"),
        )
    )


def cache_dir() -> Path:
    path = Path(os.getenv("ALTTEXT_CACHE", str(Path.home() / ".alttext")))
    path.mkdir(parents=True, exist_ok=True)
    return path
