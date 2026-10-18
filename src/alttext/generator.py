"""Alt-text generation backends."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image

from .config import model_dir


@dataclass(frozen=True, slots=True)
class AltSuggestion:
    alt: str
    decorative: bool = False
    text_in_image: str = ""
    confidence: float = 0.0
    notes: str = ""
    long_alt: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "alt": self.alt,
            "decorative": self.decorative,
            "text_in_image": self.text_in_image,
            "confidence": round(self.confidence, 3),
            "notes": self.notes,
            "long_alt": self.long_alt,
        }


class Generator(Protocol):
    name: str

    def suggest(self, image: Image.Image, context: str = "") -> AltSuggestion: ...


class HeuristicGenerator:
    """Deterministic fallback for tests and demos without weights."""

    name = "heuristic"

    def suggest(self, image: Image.Image, context: str = "") -> AltSuggestion:
        label = context.strip() or "image"
        width, height = image.size
        orientation = "wide" if width > height else "tall" if height > width else "square"
        alt = f"{label}, {orientation} image, {width} by {height} pixels"
        return AltSuggestion(alt=alt[:160], confidence=0.2, notes="heuristic")


PROMPT = """You write alt text for a blind reader. Return one JSON object only.

Rules:
- Describe the image purpose and the information it carries, not its visual style.
- Keep it under 160 characters.
- Do not start with "image of" or "photo of".
- If the image is decorative and carries no information, set decorative true and alt empty.
- If text appears in the image, copy at most 120 characters into text_in_image, with no newlines.
- For a chart, diagram, or dense infographic, write a long_alt of one to three sentences, under 500 characters. State the chart type and key values. Do not claim a trend unless every step supports it. Otherwise leave long_alt empty.
- If you are unsure, use a lower confidence.

Context: {context}

JSON shape:
{{"alt": "...", "decorative": false, "text_in_image": "", "confidence": 0.0, "notes": "", "long_alt": ""}}
"""

PREFIXES = (
    "the image shows ",
    "the image is ",
    "this image shows ",
    "this image is ",
    "the picture shows ",
    "a picture of ",
    "an image of ",
    "image of ",
    "photo of ",
)


def clean_caption(text: str) -> str:
    value = " ".join(text.split()).strip()
    lowered = value.lower()
    for prefix in PREFIXES:
        if lowered.startswith(prefix):
            value = value[len(prefix) :]
            break
    value = value.rstrip(". ").strip()
    if value and value[0].islower():
        value = value[0].upper() + value[1:]
    return value[:160]


def sanitize_text_in_image(value: object, context: str = "") -> str:
    text = " ".join(str(value or "").split())
    if len(text) < 8:
        return ""
    if context and text.casefold() == context.strip().casefold():
        return ""
    return text[:300]


def parse_model_reply(text: str) -> dict[str, object]:
    value = text.strip()
    start, end = value.find("{"), value.rfind("}")
    if start >= 0 and end > start:
        value = value[start : end + 1]
    return json.loads(value)


class MlxQwenGenerator:
    """Qwen3-VL-2B, 4-bit, on Apple Metal through MLX."""

    name = "qwen3-vl-2b-4bit"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or model_dir()
        self._model = None
        self._processor = None
        self._generate = None
        self._template = None

    def _load(self) -> None:
        if self._model is not None:
            return
        if not (self.path / "model.safetensors").exists():
            raise RuntimeError(
                f"model not found at {self.path}. Run: python scripts/download_model.py"
            )
        try:
            from mlx_vlm import generate, load
            from mlx_vlm.prompt_utils import apply_chat_template
        except ImportError as exc:
            raise RuntimeError(
                "MLX is not installed. Install with: uv pip install -e '.[model]'"
            ) from exc
        self._generate = generate
        self._template = apply_chat_template
        self._model, self._processor = load(str(self.path))

    def suggest(self, image: Image.Image, context: str = "") -> AltSuggestion:
        self._load()
        assert self._model is not None and self._processor is not None
        image = image.convert("RGB")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            temp = Path(handle.name)
        try:
            image.save(temp)
            prompt = self._template(
                self._processor,
                self._model.config,
                PROMPT.format(context=context or "none"),
                num_images=1,
            )
            result = self._generate(
                self._model,
                self._processor,
                prompt,
                str(temp),
                max_tokens=260,
                verbose=False,
            )
        finally:
            temp.unlink(missing_ok=True)
        text = str(result.text).strip()
        try:
            data = parse_model_reply(text)
        except (ValueError, json.JSONDecodeError):
            match = re.search(r'"alt"\s*:\s*"((?:\\.|[^"\\])*)"', text)
            if match:
                try:
                    recovered = json.loads(f'"{match.group(1)}"')
                except json.JSONDecodeError:
                    recovered = match.group(1)
                return AltSuggestion(
                    alt=clean_caption(recovered),
                    confidence=0.4,
                    notes="recovered alt from a truncated reply",
                )
            return AltSuggestion(
                alt=clean_caption(text),
                confidence=0.3,
                notes="unstructured model reply",
            )
        alt = clean_caption(str(data.get("alt") or ""))
        decorative = bool(data.get("decorative"))
        return AltSuggestion(
            alt="" if decorative else alt,
            decorative=decorative,
            text_in_image=sanitize_text_in_image(data.get("text_in_image"), context),
            confidence=max(0.0, min(1.0, float(data.get("confidence") or 0.0))),
            notes=str(data.get("notes") or "")[:200],
            long_alt=" ".join(str(data.get("long_alt") or "").split())[:500],
        )


def build_generator(name: str = "auto") -> Generator:
    name = (name or "auto").lower()
    if name in {"heuristic", "none"}:
        return HeuristicGenerator()
    if name in {"auto", "qwen", "mlx", "qwen3-vl-2b-4bit"}:
        folder = model_dir()
        if (folder / "model.safetensors").exists():
            return MlxQwenGenerator(folder)
        if name == "auto":
            return HeuristicGenerator()
        raise RuntimeError("Qwen model not found. Run: python scripts/download_model.py")
    raise ValueError(f"unknown generator: {name}")
