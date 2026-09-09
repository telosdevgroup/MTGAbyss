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
        assert guide["title"] in html.unescape(res.text)
    assert "Ready to Build Your Next Commander Masterpiece?" in res.text
    assert 'href="/commander"' in res.text

def test_guide_detail_pages_render_and_have_schema():
    """Verify individual guide pages render content, takeaways, card references, and Schema.org metadata."""
    for slug, guide in GUIDES.items():
        res = client.get(f"/guides/{slug}", headers={"host": "avascry.com"})
        assert res.status_code == 200
        assert guide["title"] in html.unescape(res.text)
        assert "Key Takeaways" in res.text
        assert "https://schema.org" in res.text
        assert "TechArticle" in res.text
        if guide.get("hero_card"):
            assert "Featured Artwork" in res.text
            assert "Cards with Similar Art" in res.text
            assert "mtg card" in res.text

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

def test_sitemaps_contain_guides():
    """Verify that sitemap-guides.xml, sitemap.html, sitemap.md, and llms.txt all contain all guide URLs."""
    for sitemap_url in ["/sitemap-guides.xml", "/sitemap.html", "/sitemap.md", "/llms.txt"]:
        res = client.get(sitemap_url, headers={"host": "avascry.com"})
        assert res.status_code == 200
        assert "avascry.com/guides" in res.text or "/guides" in res.text
        for slug in GUIDES.keys():
            assert slug in res.text

    # Main sitemap.xml links to the catalog and the standalone guides sitemap
    res_main = client.get("/sitemap.xml", headers={"host": "avascry.com"})
    assert res_main.status_code == 200
    assert "https://avascry.com/guides" in res_main.text
    assert "https://avascry.com/sitemap-guides.xml" in res_main.text


def test_dedicated_guides_sitemaps_exist_and_render_all_guides():
    """Verify dedicated sitemap-guides.xml, sitemaps/guides.html, and sitemaps/guides.md."""
    for sitemap_url in ["/sitemap-guides.xml", "/sitemaps/guides.html", "/sitemaps/guides.md"]:
        res = client.get(sitemap_url, headers={"host": "avascry.com"})
        assert res.status_code == 200
        for slug in GUIDES.keys():
            assert slug in res.text

    # Verify XML content-type and tags
    res_xml = client.get("/sitemap-guides.xml", headers={"host": "avascry.com"})
    assert res_xml.status_code == 200
    assert "application/xml" in res_xml.headers.get("content-type", "")
    assert "<urlset" in res_xml.text

    # Verify robots.txt declares sitemap-guides.xml
    res_robots = client.get("/robots.txt", headers={"host": "avascry.com"})
    assert res_robots.status_code == 200
    assert "https://avascry.com/sitemap-guides.xml" in res_robots.text


def test_card_name_shortcut_resolves_to_english_oracle_printing():
    """Verify /card/<slug> shortcuts resolve to canonical English Oracle printings."""
    for slug in ["sol-ring", "swords-to-plowshares", "rhystic-study", "beast-within"]:
        res = client.get(f"/card/{slug}", headers={"host": "avascry.com"}, follow_redirects=False)
        assert res.status_code == 303
        loc = res.headers.get("location")
        assert loc.startswith("/printing/")
        # Follow the redirect and verify card page is in English
        detail_res = client.get(loc, headers={"host": "avascry.com"})
        assert detail_res.status_code == 200
        # Main h1 title and hero image alt must display English card name
        card_name_normalized = slug.replace('-', ' ')
        assert f">{card_name_normalized}<" in detail_res.text.lower() or f"alt=\"{card_name_normalized}" in detail_res.text.lower()

