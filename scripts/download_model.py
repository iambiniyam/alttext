#!/usr/bin/env python3
"""Download the 4-bit Qwen3-VL model used by alttext."""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

REPO = "mlx-community/Qwen3-VL-2B-Instruct-4bit"
FILES = (
    "added_tokens.json",
    "chat_template.jinja",
    "chat_template.json",
    "config.json",
    "generation_config.json",
    "merges.txt",
    "model.safetensors",
    "model.safetensors.index.json",
    "preprocessor_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "video_preprocessor_config.json",
    "vocab.json",
)


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=300) as response, temp.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    temp.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, default=Path.home() / ".alttext" / "models" / "qwen3-vl-2b-4bit")
    args = parser.parse_args()
    base = f"https://huggingface.co/{REPO}/resolve/main"
    for name in FILES:
        target = args.dest / name
        if target.exists() and target.stat().st_size > 100:
            print(f"skip {name}")
            continue
        print(f"-> {base}/{name}")
        try:
            fetch(f"{base}/{name}", target)
        except Exception as exc:  # noqa: BLE001 - report download failures cleanly
            print(f"failed: {exc}", file=sys.stderr)
            return 1
    print(f"done: {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
