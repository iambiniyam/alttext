from PIL import Image

from alttext.generator import (
    HeuristicGenerator,
    build_generator,
    clean_caption,
    sanitize_text_in_image,
)


def test_heuristic_generator_is_deterministic():
    image = Image.new("RGB", (200, 100), "white")
    first = HeuristicGenerator().suggest(image, context="dashboard")
    second = HeuristicGenerator().suggest(image, context="dashboard")
    assert first == second
    assert "dashboard" in first.alt
    assert "wide" in first.alt


def test_clean_caption_removes_meta_prefixes():
    assert clean_caption("The image shows a green maize leaf.") == "A green maize leaf"
    assert clean_caption("photo of a receipt") == "A receipt"


def test_build_heuristic_generator():
    assert isinstance(build_generator("heuristic"), HeuristicGenerator)


def test_context_is_not_text_in_image():
    assert sanitize_text_in_image("plant health article", "plant health article") == ""
    assert sanitize_text_in_image("TOTAL $14.58", "") == "TOTAL $14.58"
    assert sanitize_text_in_image("short", "") == ""


def test_long_alt_round_trip():
    from alttext.generator import AltSuggestion

    suggestion = AltSuggestion(alt="Sales chart", long_alt="Sales rise through Q3.")
    payload = suggestion.to_dict()
    assert payload["long_alt"] == "Sales rise through Q3."
