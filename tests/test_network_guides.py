import html
from fastapi.testclient import TestClient
from app import app
from mtgabyss.data.minecraft_guides import MINECRAFT_GUIDES
from mtgabyss.data.necromunda_guides import NECROMUNDA_GUIDES

client = TestClient(app)

def test_minecraft_guides_hub_and_detail():
    """Verify Minecraft /guides and /guides/{slug} render without visible dates."""
    res = client.get("/guides", headers={"host": "minecraft.avascry.com"})
    assert res.status_code == 200
    assert "Minecraft Guides &amp; Strategy" in res.text or "Minecraft Guides & Strategy" in res.text
    for slug, guide in MINECRAFT_GUIDES.items():
        assert f"/guides/{slug}" in res.text
        # Detail test
        detail = client.get(f"/guides/{slug}", headers={"host": "minecraft.avascry.com"})
        assert detail.status_code == 200
        assert (guide["title"] in detail.text) or (html.escape(guide["title"]) in detail.text)
        assert "Key Takeaways" in detail.text
        assert "Published 202" not in detail.text  # Confirm NO visible date

def test_necromunda_guides_hub_and_detail():
    """Verify Necromunda /guides and /guides/{slug} render without visible dates."""
    res = client.get("/guides", headers={"host": "necromunda.avascry.com"})
    assert res.status_code == 200
    assert "Underhive Campaign Guides" in res.text
    for slug, guide in NECROMUNDA_GUIDES.items():
        assert f"/guides/{slug}" in res.text
        # Detail test
        detail = client.get(f"/guides/{slug}", headers={"host": "necromunda.avascry.com"})
        assert detail.status_code == 200
        assert (guide["title"] in detail.text) or (html.escape(guide["title"]) in detail.text)
        assert "Key Tactical Takeaways" in detail.text
        assert "Published 202" not in detail.text  # Confirm NO visible date

def test_mtg_guides_no_visible_dates():
    """Verify MTG guides index and detail pages have no visible published dates."""
    res = client.get("/guides", headers={"host": "avascry.com"})
    assert res.status_code == 200
    assert "Published 202" not in res.text
    detail = client.get("/guides/commander-deckbuilding-8x8", headers={"host": "avascry.com"})
    assert detail.status_code == 200
    assert "Published 202" not in detail.text
