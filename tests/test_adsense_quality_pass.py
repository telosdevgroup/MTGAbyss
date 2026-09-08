from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_methodology_page_renders_successfully():
    """Verify /methodology returns 200 OK and renders full technical documentation."""
    res = client.get("/methodology", headers={"host": "avascry.com"})
    assert res.status_code == 200
    assert "AvaScry Methodology &amp; Engineering" in res.text or "AvaScry Methodology & Engineering" in res.text
    assert "4,096-Dimensional" in res.text or "4,096-dimensional" in res.text
    assert "SmartDeck" in res.text
    assert "Scryfall API" in res.text

def test_footer_contains_methodology_link():
    """Verify footer contains direct link to Methodology & Science."""
    res = client.get("/", headers={"host": "avascry.com"})
    assert res.status_code == 200
    assert 'href="/methodology"' in res.text
    assert "Methodology &amp; Science" in res.text or "Methodology" in res.text

def test_machine_format_endpoints_have_noindex():
    """Verify raw machine formats (.json, .md, .csv, /vector/*) receive X-Robots-Tag: noindex."""
    endpoints = [
        "/vector/sol-ring.json",
        "/rules.md",
        "/rules.json",
        "/legalities.md",
        "/legalities.json",
        "/sets.md"
    ]
    for path in endpoints:
        res = client.get(path, headers={"host": "avascry.com"})
        if res.status_code == 200:
            assert "X-Robots-Tag" in res.headers, f"Missing X-Robots-Tag on {path}"
            assert "noindex" in res.headers["X-Robots-Tag"], f"noindex missing in {path}"

def test_canonical_html_pages_do_not_have_noindex():
    """Canonical HTML pages must NOT receive X-Robots-Tag: noindex."""
    html_pages = [
        "/",
        "/about",
        "/methodology",
        "/sets",
        "/commander",
        "/live-gallery"
    ]
    for path in html_pages:
        res = client.get(path, headers={"host": "avascry.com"})
        assert res.status_code == 200
        x_robots = res.headers.get("X-Robots-Tag", "")
        assert "noindex" not in x_robots, f"Unexpected noindex on HTML page {path}"

def test_manifest_and_sitemaps_exempt_from_noindex():
    """Verify core manifests remain indexable/crawler-accessible."""
    for path in ["/robots.txt", "/manifest.json", "/llms.txt", "/sitemap.xml"]:
        res = client.get(path, headers={"host": "avascry.com"})
        assert res.status_code == 200
        assert "noindex" not in res.headers.get("X-Robots-Tag", "")
