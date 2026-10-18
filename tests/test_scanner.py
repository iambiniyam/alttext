from PIL import Image

from alttext.scanner import scan_folder, scan_html, scan_markdown


def test_scan_folder_finds_images(tmp_path):
    Image.new("RGB", (40, 30), "green").save(tmp_path / "leaf.jpg")
    (tmp_path / "notes.txt").write_text("ignore me")
    result = scan_folder(tmp_path)
    assert len(result.items) == 1
    assert result.items[0].status == "missing"
    assert result.items[0].ref == "leaf.jpg"


def test_scan_html_tracks_missing_empty_and_present(tmp_path):
    Image.new("RGB", (10, 10), "red").save(tmp_path / "a.png")
    Image.new("RGB", (10, 10), "blue").save(tmp_path / "b.png")
    (tmp_path / "index.html").write_text(
        '<html><body>'
        '<img src="a.png">'
        '<img src="b.png" alt="">'
        '<figure><img src="a.png" alt="A red square"><figcaption>Red</figcaption></figure>'
        '</body></html>'
    )
    result = scan_html(tmp_path / "index.html")
    statuses = [item.status for item in result.items]
    assert statuses == ["missing", "decorative", "present"]
    assert result.items[0].context == ""


def test_scan_markdown_finds_images(tmp_path):
    Image.new("RGB", (10, 10), "white").save(tmp_path / "shot.png")
    (tmp_path / "page.md").write_text("# Demo\n\n![Screenshot](shot.png)\n")
    result = scan_markdown(tmp_path / "page.md")
    assert len(result.items) == 1
    assert result.items[0].current_alt == "Screenshot"
    assert result.items[0].status == "present"
