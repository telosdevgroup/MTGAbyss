from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_swu_home():
    response = client.get("/swu")
    assert response.status_code == 200
    assert "Star Wars: Unlimited" in response.text

def test_swu_subdomain_routing():
    response = client.get("/", headers={"host": "swu.avascry.com"})
    assert response.status_code == 200
    assert "Star Wars: Unlimited" in response.text

def test_swu_filter_aspect():
    response = client.get("/swu?aspect=Vigilance")
    assert response.status_code == 200
    assert "Vigilance" in response.text

def test_swu_card_detail_html():
    response = client.get("/swu/card/luke-skywalker-faithful-friend-sor-5")
    assert response.status_code == 200
    assert "Luke Skywalker" in response.text

def test_swu_card_markdown():
    response = client.get("/swu/card/luke-skywalker-faithful-friend-sor-5.md")
    assert response.status_code == 200
    assert "text/markdown" in response.headers.get("content-type", "")
    assert "# Luke Skywalker" in response.text

def test_swu_card_json():
    response = client.get("/swu/card/luke-skywalker-faithful-friend-sor-5.json")
    assert response.status_code == 200
    data = response.json()
    assert data.get("title") == "Luke Skywalker" or data.get("name") == "Luke Skywalker"

def test_swu_llms_txt():
    response = client.get("/swu/llms.txt")
    assert response.status_code == 200
    assert "Star Wars: Unlimited" in response.text

def test_swu_trust_pages():
    for path in ("/swu/about", "/swu/privacy", "/swu/terms", "/swu/contact"):
        res = client.get(path)
        assert res.status_code == 200

def test_swu_keywords_list():
    res = client.get("/swu/keywords")
    assert res.status_code == 200
    assert "Keywords" in res.text
    assert "Ambush" in res.text
    assert "Shielded" in res.text

def test_swu_single_keyword():
    res = client.get("/swu/keyword/sentinel")
    assert res.status_code == 200
    assert "Sentinel" in res.text
    assert "Comprehensive Rules" in res.text

def test_swu_keyword_json():
    res = client.get("/swu/keyword/sentinel.json")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Sentinel"
    assert data["slug"] == "sentinel"

def test_swu_rules_index():
    res = client.get("/swu/rules")
    assert res.status_code == 200
    assert "Comprehensive Rules" in res.text
    assert "Arenas" in res.text

def test_swu_rule_section():
    res = client.get("/swu/rule/1-1-arenas-ground-and-space")
    assert res.status_code == 200
    assert "Arenas" in res.text

def test_swu_rulings_feed():
    res = client.get("/swu/rulings")
    assert res.status_code == 200
    assert "Official Rulings" in res.text

def test_swu_errata_alias():
    res = client.get("/swu/errata")
    assert res.status_code == 200
    assert "Official Rulings" in res.text

def test_swu_sitemap_has_keywords_and_rules():
    res = client.get("/swu/sitemap.xml")
    assert res.status_code == 200
    assert "/keywords" in res.text
    assert "/rules" in res.text
    assert "/keyword/sentinel" in res.text

def test_swu_random_routes():
    res = client.get("/swu/random", follow_redirects=False)
    assert res.status_code == 307
    assert "/card/" in res.headers["location"]

    res_json = client.get("/swu/random.json")
    assert res_json.status_code == 200
    assert "slug" in res_json.json()

    res_md = client.get("/swu/random.md", follow_redirects=False)
    assert res_md.status_code == 307
    assert res_md.headers["location"].endswith(".md")


def test_swu_card_xml():
    res = client.get("/swu/card/luke-skywalker-faithful-friend-sor-5.xml")
    assert res.status_code == 200
    assert "application/xml" in res.headers.get("content-type", "")
    assert "<card>" in res.text
    assert "<title>Luke Skywalker</title>" in res.text
    assert "<slug>luke-skywalker-faithful-friend-sor-5</slug>" in res.text


def test_swu_card_rel_alternates():
    res = client.get("/swu/card/luke-skywalker-faithful-friend-sor-5")
    assert res.status_code == 200
    text = res.text
    # Check link rel="alternate" in HTML head for .md, .json, and .xml
    assert 'rel="alternate" type="text/markdown"' in text
    assert 'luke-skywalker-faithful-friend-sor-5.md' in text
    assert 'rel="alternate" type="application/json"' in text
    assert 'luke-skywalker-faithful-friend-sor-5.json' in text
    assert 'rel="alternate" type="application/xml"' in text
    assert 'luke-skywalker-faithful-friend-sor-5.xml' in text
    # Check HTTP Link header
    link_header = res.headers.get("link", "")
    assert ".xml" in link_header
    assert ".json" in link_header
    assert ".md" in link_header


def test_swu_keyword_markdown():
    res = client.get("/swu/keyword/sentinel.md")
    assert res.status_code == 200
    assert "text/markdown" in res.headers.get("content-type", "")
    assert "# Sentinel" in res.text


def test_swu_home_seo_alternates():
    res = client.get("/swu")
    assert res.status_code == 200
    text = res.text
    assert '<link rel="canonical" href="https://swu.avascry.com/">' in text
    assert '<link rel="alternate" type="application/xml"' in text
    assert 'sitemap.xml' in text
    assert '<link rel="alternate" type="text/plain"' in text
    assert 'llms.txt' in text
    assert '<meta name="content-signal" content="ai-train=yes, search=yes, ai-input=yes">' in text


def test_swu_rules_and_keywords_seo():
    res_rules = client.get("/swu/rules")
    assert res_rules.status_code == 200
    assert '<link rel="canonical" href="https://swu.avascry.com/rules">' in res_rules.text
    assert 'rules.md' in res_rules.text
    assert 'rules.json' in res_rules.text

    res_kw = client.get("/swu/keywords")
    assert res_kw.status_code == 200
    assert '<link rel="canonical" href="https://swu.avascry.com/keywords">' in res_kw.text

    res_kw_detail = client.get("/swu/keyword/sentinel")
    assert res_kw_detail.status_code == 200
    assert '<link rel="canonical" href="https://swu.avascry.com/keyword/sentinel">' in res_kw_detail.text
    assert 'sentinel.json' in res_kw_detail.text
    assert 'sentinel.md' in res_kw_detail.text


def test_swu_trust_pages_canonicals():
    for page in ("about", "privacy", "terms", "contact"):
        res = client.get(f"/swu/{page}")
        assert res.status_code == 200
        assert f'<link rel="canonical" href="https://swu.avascry.com/{page}">' in res.text
        assert '<link rel="alternate" type="application/xml"' in res.text
        assert 'sitemap.xml' in res.text
        assert "â€”" not in res.text


def test_swu_rulings_feed_seo():
    res = client.get("/swu/rulings")
    assert res.status_code == 200
    assert '<link rel="canonical" href="https://swu.avascry.com/rulings">' in res.text
    assert '<link rel="alternate" type="application/xml"' in res.text
    assert "â€”" not in res.text



