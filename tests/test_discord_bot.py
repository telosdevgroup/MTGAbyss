import json
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from app import app
from mtgabyss.routers.discord_bot_router import verify_discord_signature

client = TestClient(app)

def test_ed25519_signature_verification():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_hex = public_key.public_bytes_raw().hex()

    timestamp = "1720000000"
    body = b'{"type":1}'
    message = timestamp.encode("utf-8") + body
    sig_hex = private_key.sign(message).hex()

    assert verify_discord_signature(sig_hex, timestamp, body, pub_hex) is True
    assert verify_discord_signature("deadbeef" * 8, timestamp, body, pub_hex) is False

def test_discord_ping():
    # Discord Type 1 PING
    resp = client.post("/api/discord/interactions", json={"type": 1})
    assert resp.status_code == 200
    assert resp.json() == {"type": 1}

def test_discord_necro_slash_command():
    payload = {
        "type": 2,
        "data": {
            "name": "necro",
            "options": [
                {
                    "name": "weapon",
                    "options": [
                        {"name": "name", "value": "bolter"}
                    ]
                }
            ]
        }
    }
    resp = client.post("/api/discord/interactions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == 4
    embeds = data["data"].get("embeds", [])
    assert len(embeds) > 0
    assert "bolter" in embeds[0]["title"].lower()
    assert "https://necromunda.avascry.com/weapon/" in embeds[0]["url"]

def test_discord_swu_slash_command():
    payload = {
        "type": 2,
        "data": {
            "name": "swu",
            "options": [
                {
                    "name": "card",
                    "options": [
                        {"name": "name", "value": "luke"}
                    ]
                }
            ]
        }
    }
    resp = client.post("/api/discord/interactions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == 4
    embeds = data["data"].get("embeds", [])
    assert len(embeds) > 0
    assert "Luke" in embeds[0]["title"]
    assert "https://swu.avascry.com/card/" in embeds[0]["url"]

def test_discord_minecraft_slash_command():
    payload = {
        "type": 2,
        "data": {
            "name": "mc",
            "options": [
                {
                    "name": "item",
                    "options": [
                        {"name": "name", "value": "diamond"}
                    ]
                }
            ]
        }
    }
    resp = client.post("/api/discord/interactions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == 4
    embeds = data["data"].get("embeds", [])
    assert len(embeds) > 0
    assert "Diamond" in embeds[0]["title"]
