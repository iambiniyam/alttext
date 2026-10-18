"""Bounded HTML fetch for auditing a public page without a browser."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .scanner import AltItem, ScanResult, _status

MAX_BYTES = 5 * 1024 * 1024


def scan_url(url: str, timeout: float = 15.0) -> ScanResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "alttext/0.1 (+local accessibility audit)"},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        if len(response.content) > MAX_BYTES:
            raise ValueError(f"page is larger than {MAX_BYTES // (1024 * 1024)} MB")
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type:
            raise ValueError(f"expected HTML, got {content_type or 'unknown content type'}")
        soup = BeautifulSoup(response.text, "html.parser")
        result = ScanResult()
        for image in soup.find_all("img"):
            src = (image.get("src") or image.get("data-src") or "").strip()
            if not src or src.startswith("data:"):
                continue
            absolute = urljoin(str(response.url), src)
            parent = image.find_parent(["figure", "a", "p", "div"])
            context = " ".join(parent.get_text(" ", strip=True).split())[:240] if parent else ""
            result.items.append(
                AltItem(
                    ref=absolute,
                    source=absolute,
                    kind="url",
                    current_alt=image.get("alt"),
                    context=context,
                    status=_status(image.get("alt")),
                )
            )
        if not result.items:
            result.warnings.append("no <img> elements found on the page")
        return result
