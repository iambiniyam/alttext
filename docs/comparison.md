# Comparison

## Similar tools

- [Nutlope alt-text-generator](https://github.com/Nutlope/alt-text-generator) is a small cloud API around BLIP.
- [WAVE](https://wave.webaim.org/) and Accessibility Insights audit pages, but they do not generate local captions.
- Most alt-text demos handle one image at a time.

## What alttext does differently

- Local Qwen3-VL 4-bit on Apple MLX, with a heuristic fallback for tests.
- Audits folders, HTML, Markdown, DOCX, and public HTML pages, from the CLI or the web UI.
- Produces a reviewable report and can patch HTML.
- Ships a GitHub Action that fails a workflow on missing alt text.

## Tradeoff

WAVE has deeper rule coverage and browser-rendered checks. alttext focuses on the image-level audit and the draft, and it does not replace a full WCAG evaluation.
