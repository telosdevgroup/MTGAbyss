from starlette.testclient import TestClient
from app import app

client = TestClient(app, follow_redirects=True)

def test_minecraft_legal_endpoints_subdomain():
    headers = {"host": "minecraft.avascry.com"}
    
    r = client.get("/about", headers=headers)
    assert r.status_code == 200
    assert "About AvaScry Minecraft" in r.text

    r = client.get("/privacy", headers=headers)
    assert r.status_code == 200
    assert "Privacy Policy" in r.text
    assert "AvaScry Minecraft" in r.text

    r = client.get("/terms", headers=headers)
    assert r.status_code == 200
    assert "Terms of Service" in r.text
    assert "AvaScry Minecraft" in r.text

    r = client.get("/contact", headers=headers)
    assert r.status_code == 200
    assert "Contact AvaScry Minecraft" in r.text

def test_minecraft_legal_endpoints_prefix():
    r = client.get("/minecraft/about")
    assert r.status_code == 200
    assert "About AvaScry Minecraft" in r.text

    r = client.get("/minecraft/privacy")
    assert r.status_code == 200
    assert "Privacy Policy" in r.text

    r = client.get("/minecraft/terms")
    assert r.status_code == 200
    assert "Terms of Service" in r.text

    r = client.get("/minecraft/contact")
    assert r.status_code == 200
    assert "Contact AvaScry Minecraft" in r.text

def test_minecraft_contact_post():
    from unittest.mock import patch, AsyncMock
    with patch("mtgabyss.routers.auth_router.send_discord_notification", new_callable=AsyncMock) as mock_notify:
        r = client.post("/minecraft/contact", data={
            "name": "Steve",
            "contact": "steve@example.com",
            "category": "errata",
            "message": "The diamond pickaxe harvest speed needs update."
        })
        assert r.status_code == 200
        assert "Thank you" in r.text

