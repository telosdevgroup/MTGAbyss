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

