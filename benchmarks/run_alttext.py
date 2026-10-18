"""Run the local model over images and record suggestions and latency."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from PIL import Image

from alttext.generator import build_generator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, default=Path("docs/model-run.json"))
    args = parser.parse_args()
    generator = build_generator("qwen")
    rows = []
    for path in sorted(args.folder.iterdir()):
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        image = Image.open(path)
        started = time.perf_counter()
        suggestion = generator.suggest(image, context=path.stem.replace("_", " "))
        elapsed = round((time.perf_counter() - started) * 1000)
        rows.append({"file": path.name, **suggestion.to_dict(), "ms": elapsed})
        print(path.name, elapsed, suggestion.alt)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
