import pytest
from starlette.testclient import TestClient
from app import app
from mtgabyss.routers.auth_router import is_safe_redirect

client = TestClient(app, raise_server_exceptions=False)

def test_is_safe_redirect_allowed_paths():
    """Verify legitimate relative internal paths are allowed."""
    assert is_safe_redirect("/dashboard") is True
    assert is_safe_redirect("/commander") is True
    assert is_safe_redirect("/set/mh3") is True
    assert is_safe_redirect("/printing/sol-ring-sld") is True
    assert is_safe_redirect("/artist/rebecca-guay") is True

def test_is_safe_redirect_rejects_external_schemes():
    """Verify full absolute URLs with schemes are rejected."""
    assert is_safe_redirect("https://evil.com") is False
    assert is_safe_redirect("http://evil.com") is False
    assert is_safe_redirect("http://avascry.com.evil.com") is False
    assert is_safe_redirect("javascript:alert(1)") is False

def test_is_safe_redirect_rejects_protocol_relative():
    """Verify protocol-relative URLs (//attacker.com) are rejected."""
    assert is_safe_redirect("//evil.com") is False
    assert is_safe_redirect("//evil.com/path") is False
    assert is_safe_redirect("///evil.com") is False

def test_is_safe_redirect_rejects_backslash_and_auth_loops():
    """Verify Windows backslash tricks and auth route loops are rejected."""
    assert is_safe_redirect(r"\evil.com") is False
    assert is_safe_redirect(r"/\\evil.com") is False
    assert is_safe_redirect("/auth/login") is False
    assert is_safe_redirect("/auth/google/callback") is False
    assert is_safe_redirect(None) is False
    assert is_safe_redirect("") is False

def test_auth_login_sanitizes_next_parameter(monkeypatch):
    """Verify /auth/discord/login with external ?next= falls back safely to /dashboard."""
    monkeypatch.setenv("DISCORD_CLIENT_ID", "dummy_client")
    response = client.get("/auth/discord/login?next=https://evil.com", follow_redirects=False)
    assert response.status_code == 303
    auth_url = response.headers.get("location", "")
    assert "discord.com/oauth2/authorize" in auth_url

def test_auth_logout_sanitizes_external_redirect():
    """Verify /auth/logout with external ?next= safely redirects to /commander."""
    response = client.get("/auth/logout?next=https://evil.com", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/commander"

def test_auth_callback_missing_saved_state_rejected():
    """Verify Discord callback without prior session state is immediately rejected."""
    response = client.get("/auth/discord/callback?code=fake_code&state=fake_state", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login?auth_error=" in response.headers.get("location", "")

def test_auth_callback_state_mismatch_rejected(monkeypatch):
    """Verify Discord callback with tampered state parameter is rejected."""
    monkeypatch.setenv("DISCORD_CLIENT_ID", "dummy_client")
    login_resp = client.get("/auth/discord/login", follow_redirects=False)
    assert login_resp.status_code == 303
    
    callback_resp = client.get("/auth/discord/callback?code=fake_code&state=wrong_mismatched_state", follow_redirects=False)
    assert callback_resp.status_code == 303
    assert "/auth/login?auth_error=" in callback_resp.headers.get("location", "")
