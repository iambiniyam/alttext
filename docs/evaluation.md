# Alt-text model evaluation

This is a small qualitative check of the local Qwen3-VL-2B 4-bit model on the bundled example images. It is not a benchmark with reference alt text.

## Hardware

- Apple Silicon Mac with 8 GB RAM.
- macOS.
- `mlx-vlm` 0.7.8.
- Qwen3-VL-2B-Instruct 4-bit MLX, about 1.7 GB.

The full fp16 model is about 4.3 GB. It loaded but did not complete generation on this 8 GB machine, even with swap. The 4-bit MLX build is the version used by the tool.

## Method

1. Load the model once.
2. Send the image with the alt-text JSON prompt.
3. Record the alt text, text-in-image, confidence, and latency.
4. Review the result by hand.

Prompt requirements: purpose over style, under 160 characters, no "image of", allow decorative, copy important text into a separate field.

## Results

| Image | Alt text | Latency | Review |
|---|---|---|---|
| `maize_rust.jpg` | A close-up of a green leaf with visible veins and minor blemishes | 9.5 s | Accurate, but too neutral for a disease article. It does not claim rust. |
| `receipt.png` | Receipt for Blue Bottle Coffee with items and total amount | 18.2 s | Correct but generic. The text field captured the items and total. |
| `interface.png` | A close-up of a diseased maize leaf with orange-brown spots | 25.5 s | Correct about the leaf, but it does not say this is a screenshot. |

## What works

- The model identifies leaves, receipts, and people without cloud calls.
- It follows the JSON shape in most runs.
- It recovers the alt field when the JSON is truncated.
- It copies receipt text into the separate text field, which is useful for review.
- The 4-bit build fits an 8 GB laptop and runs in seconds.

## What does not

- Screenshots are treated as their visual content, not as an app screen.
- Generic documents get a generic alt. A human should add the issuer, date, and amount.
- The model sometimes repeats the context into `text_in_image`. The tool now clears that when it exactly matches the context.
- There is no reference alt text, so this is not a top-1 or BLEU score.

## Decision

Use Qwen3-VL-2B 4-bit MLX as the default. It is the best quality that fits the hardware. Keep the heuristic fallback for tests and machines without MLX. Florence-2 was tested as a fallback but produced vaguer captions and needed an older Transformers stack, so it is not shipped.


## URL scanning check

- A local HTML test page with one missing alt and one present alt produced 1 missing and 1 present result.
- Data URIs were ignored.
- A non-HTTP scheme was rejected.
- The scanner fetches HTML only; it does not run JavaScript.


## Long descriptions

The model now returns an optional `long_alt` for charts, diagrams, and dense images. The review UI exposes it in a second field and includes it in JSON and CSV exports. A synthetic chart was not available for this round, so the long-description path is covered by a data-model test, not a visual quality benchmark.
