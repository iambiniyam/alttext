import json

from bs4 import BeautifulSoup

from alttext.generator import AltSuggestion
from alttext.report import apply_html, rows
from alttext.scanner import AltItem


def test_rows_merge_suggestions():
    item = AltItem("a.png", "/tmp/a.png", "html", None, "checkout", "missing")
    records = rows([item], [AltSuggestion("A green checkout button", confidence=0.9)])
    assert records[0]["suggested_alt"] == "A green checkout button"
    assert records[0]["status"] == "missing"


def test_apply_html_patches_matching_src(tmp_path):
    html = tmp_path / "index.html"
    html.write_text('<html><body><img src="a.png"><img src="b.png" alt="keep"></body></html>')
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"items": [{"ref": "a.png", "suggested_alt": "A red square"}]}))
    out = tmp_path / "fixed.html"
    apply_html(report, html, out)
    soup = BeautifulSoup(out.read_text(), "html.parser")
    images = soup.find_all("img")
    assert images[0]["alt"] == "A red square"
    assert images[1]["alt"] == "keep"
