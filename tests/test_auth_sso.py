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
    assert 'href="/auth/discord/login"' in res.text
    assert 'Sign In with Discord' in res.text

def test_dominion_renders_sign_in_when_anonymous():
    res = client.get("/", headers={"host": "dominion.avascry.com"})
    assert res.status_code == 200
    assert 'href="/auth/discord/login"' in res.text
    assert 'Sign In with Discord' in res.text

def test_necromunda_renders_sign_in_when_anonymous():
    res = client.get("/necromunda")
    assert res.status_code == 200
    assert 'href="/auth/discord/login"' in res.text
    assert 'Sign In with Discord' in res.text

def test_mtg_renders_sign_in_when_anonymous():
    res = client.get("/")
    assert res.status_code == 200
    assert 'href="/auth/discord/login"' in res.text
    assert 'Sign In with Discord' in res.text

def test_subsite_auth_login_not_found_fixed():
    for sub_host in ["swu.avascry.com", "dominion.avascry.com", "necromunda.avascry.com"]:
        res = client.get("/auth/login", headers={"host": sub_host})
        assert res.status_code == 200
        assert "Sign in to AvaScry" in res.text
        assert '{"detail":"Not Found"}' not in res.text

def test_subsite_auth_logout_redirects_to_subsite_home():
    for sub_host in ["swu.avascry.com", "dominion.avascry.com", "necromunda.avascry.com"]:
        res = client.get("/auth/logout", headers={"host": sub_host}, follow_redirects=False)
        assert res.status_code == 303
        assert res.headers["location"] == f"http://{sub_host}/"

def test_primary_auth_logout_redirects_to_home():
    res = client.get("/auth/logout", headers={"host": "avascry.com"}, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/"
    # Verify cookie clearance headers
    raw_cookies = res.headers.get_list("set-cookie")
    assert len(raw_cookies) > 0
    cookies_str = " ".join(raw_cookies)
    assert "avascry_session" in cookies_str
    assert "domain=.avascry.com" in cookies_str.lower()

def test_subsite_oauth_login_flow(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "dummy_discord_client")
    
    # Subsite Discord Login
    res_discord = client.get("/auth/discord/login", headers={"host": "swu.avascry.com"}, follow_redirects=False)
    assert res_discord.status_code == 303
    loc = res_discord.headers["location"]
    assert "https://discord.com/oauth2/authorize" in loc
    assert "redirect_uri=https%3A%2F%2Favascry.com%2Fauth%2Fdiscord%2Fcallback" in loc

def test_network_session_cookie_domain_on_avascry_hosts(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "dummy_discord_client")
    
    # On Dominion subsite: cookie must have Domain=.avascry.com
    res_dom = client.get("/auth/discord/login", headers={"host": "dominion.avascry.com"}, follow_redirects=False)
    assert res_dom.status_code == 303
    set_cookie = res_dom.headers.get("set-cookie", "")
    assert "domain=.avascry.com" in set_cookie.lower()
    
    # On primary MTG site: cookie must also have Domain=.avascry.com
    res_mtg = client.get("/auth/discord/login", headers={"host": "avascry.com"}, follow_redirects=False)
    assert res_mtg.status_code == 303
    set_cookie_mtg = res_mtg.headers.get("set-cookie", "")
    assert "domain=.avascry.com" in set_cookie_mtg.lower()

    # On testserver / localhost: no domain assigned to prevent browser rejection
    res_local = client.get("/auth/discord/login", headers={"host": "localhost:8004"}, follow_redirects=False)
    assert res_local.status_code == 303
    set_cookie_local = res_local.headers.get("set-cookie", "")
    assert "domain=" not in set_cookie_local.lower()

def test_cross_subdomain_oauth_state_shared(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "dummy_discord_client")
    
    # 1. User starts login on dominion.avascry.com
    res_start = client.get("/auth/discord/login", headers={"host": "dominion.avascry.com"}, follow_redirects=False)
    assert res_start.status_code == 303
    
    # Extract state parameter from authorize redirect URL
    from urllib.parse import urlparse, parse_qs
    loc = res_start.headers["location"]
    parsed = urlparse(loc)
    state = parse_qs(parsed.query)["state"][0]
    
    # Extract session cookie
    raw_cookie = res_start.headers["set-cookie"]
    cookie_val = raw_cookie.split(";")[0]
    
    # 2. User returns to canonical avascry.com callback with the shared cookie
    res_callback = client.get(
        f"/auth/discord/callback?code=mock_code&state={state}",
        headers={"host": "avascry.com", "cookie": cookie_val},
        follow_redirects=False
    )
    # Crucial assertion: Must NOT return invalid_oauth_state!
    loc_cb = res_callback.headers.get("location", "")
    assert "invalid_oauth_state" not in loc_cb

def test_subsite_oauth_login_referer_preserved(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "dummy_discord_client")
    res = client.get(
        "/auth/discord/login",
        headers={"host": "swu.avascry.com", "referer": "https://swu.avascry.com/card/luke-skywalker"},
        follow_redirects=False
    )
    assert res.status_code == 303

def test_discord_login_no_forced_consent(monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_ID", "dummy_discord_client")
    res = client.get("/auth/discord/login", headers={"host": "necromunda.avascry.com"}, follow_redirects=False)
    assert res.status_code == 303
    loc = res.headers["location"]
    assert "prompt=consent" not in loc

def test_discord_login_popup_callback_html(monkeypatch):
    res_start = client.get("/auth/discord/login?popup=1", headers={"host": "necromunda.avascry.com"}, follow_redirects=False)
    cookie_val = res_start.headers["set-cookie"].split(";")[0]
    
    err_res = client.get(
        "/auth/discord/callback?error=access_denied",
        headers={"host": "avascry.com", "cookie": cookie_val},
        follow_redirects=False
    )
    assert err_res.status_code == 200
    assert "window.close();" in err_res.text
