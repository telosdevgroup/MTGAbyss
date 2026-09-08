import html
from fastapi.testclient import TestClient
from app import app
from mtgabyss.data.guides import GUIDES

client = TestClient(app)

def test_guides_catalog_renders_all_guides():
    """Verify /guides returns 200 OK and lists all published guides."""
    res = client.get("/guides", headers={"host": "avascry.com"})
    assert res.status_code == 200
    assert "AvaScry Strategy &amp; Guides" in res.text or "AvaScry Strategy & Guides" in res.text
    for slug, guide in GUIDES.items():
        assert f"/guides/{slug}" in res.text
        assert (guide["title"] in res.text) or (html.escape(guide["title"]) in res.text)
    assert "Ready to Build Your Next Commander Masterpiece?" in res.text
    assert 'href="/commander"' in res.text

def test_guide_detail_pages_render_and_have_schema():
    """Verify individual guide pages render content, takeaways, card references, and Schema.org metadata."""
    for slug, guide in GUIDES.items():
        res = client.get(f"/guides/{slug}", headers={"host": "avascry.com"})
        assert res.status_code == 200
        assert (guide["title"] in res.text) or (html.escape(guide["title"]) in res.text)
        assert "Key Takeaways" in res.text
        assert "https://schema.org" in res.text
        assert "TechArticle" in res.text
        assert f"https://avascry.com/guides/{slug}" in res.text

def test_nonexistent_guide_returns_404():
    """Verify requesting an invalid guide slug returns 404."""
    res = client.get("/guides/non-existent-guide-slug", headers={"host": "avascry.com"})
    assert res.status_code == 404

def test_nav_and_footer_contain_guides_link():
    """Verify top navbar and footer include link to /guides."""
    res = client.get("/", headers={"host": "avascry.com"})
    assert res.status_code == 200
    assert 'href="/guides"' in res.text

def test_set_detail_contains_explorer_guide():
    """Verify /set/mh3 contains Set Overview & Explorer Guide block."""
    res = client.get("/set/mh3", headers={"host": "avascry.com"})
    assert res.status_code == 200
    assert "Set Overview &amp; Explorer Guide" in res.text or "Set Overview & Explorer Guide" in res.text
    assert 'href="/guides"' in res.text
    assert '<link rel="canonical" href="https://avascry.com/set/mh3">' in res.text
