from fastapi.testclient import TestClient
from app import app
from mtgabyss.routers.auth_router import is_safe_redirect

client = TestClient(app)

def test_is_safe_redirect():
    # Local safe paths
    assert is_safe_redirect("/dashboard") is True
    assert is_safe_redirect("/card/luke-skywalker") is True
    assert is_safe_redirect("/dominion") is True
    assert is_safe_redirect("/swu/card/123") is True
    
    # Block unsafe/auth paths
    assert is_safe_redirect("/auth/login") is False
    assert is_safe_redirect("/auth/discord/callback") is False
    assert is_safe_redirect("//evil.com") is False
    assert is_safe_redirect("/\\evil.com") is False
    assert is_safe_redirect("javascript:alert(1)") is False
    assert is_safe_redirect(None) is False
    assert is_safe_redirect("") is False
    
    # Block external untrusted domains
    assert is_safe_redirect("https://evil.com/dashboard") is False
    assert is_safe_redirect("http://attacker.org") is False
    assert is_safe_redirect("https://avascry.com.evil.com") is False
    
    # Allow trusted AvaScry network subdomains
    assert is_safe_redirect("https://avascry.com/") is True
    assert is_safe_redirect("https://avascry.com/dashboard") is True
    assert is_safe_redirect("https://swu.avascry.com/card/luke-skywalker") is True
    assert is_safe_redirect("https://dominion.avascry.com/random") is True
    assert is_safe_redirect("https://necromunda.avascry.com/weapons") is True
    assert is_safe_redirect("http://localhost:8004/swu") is True
    assert is_safe_redirect("http://swu.localhost:8004/card/123") is True

    # Block auth paths even on trusted subdomains
    assert is_safe_redirect("https://swu.avascry.com/auth/login") is False

def test_swu_renders_sign_in_when_anonymous():
    res = client.get("/swu")
    assert res.status_code == 200
    assert 'href="/auth/login"' in res.text
    assert 'Sign In' in res.text

def test_dominion_renders_sign_in_when_anonymous():
    res = client.get("/dominion")
    assert res.status_code == 200
    assert 'href="/auth/login"' in res.text
    assert 'Sign In' in res.text

def test_necromunda_renders_sign_in_when_anonymous():
    res = client.get("/necromunda")
    assert res.status_code == 200
    assert 'href="/auth/login"' in res.text
    assert 'Sign In' in res.text
