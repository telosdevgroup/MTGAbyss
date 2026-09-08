from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_privacy_policy_contains_adsense_disclosures():
    """Privacy policy must explicitly mention AdSense, third-party cookies, and opt-outs."""
    res = client.get("/privacy", headers={"host": "avascry.com"})
    assert res.status_code == 200
    text = res.text
    assert "Google AdSense" in text
    assert "adssettings.google.com" in text
    assert "aboutads.info" in text
    assert "Discord OAuth" in text

def test_adsense_meta_account_always_present():
    """The Google AdSense verification meta tag must be present across all pages for ownership verification."""
    for path in ["/", "/auth/login", "/privacy", "/terms", "/contact"]:
        res = client.get(path, headers={"host": "avascry.com"})
        assert res.status_code == 200
        assert '<meta name="google-adsense-account" content="ca-pub-7283717447639840">' in res.text

def test_adsense_script_included_on_content_pages():
    """AdSense adsbygoogle.js script must load on content and homepage."""
    res = client.get("/", headers={"host": "avascry.com"})
    assert res.status_code == 200
    assert "adsbygoogle.js" in res.text

def test_adsense_script_suppressed_on_utility_pages():
    """AdSense adsbygoogle.js script must NOT load on utility, auth, and legal pages."""
    utility_paths = ["/auth/login", "/privacy", "/terms", "/contact"]
    for path in utility_paths:
        res = client.get(path, headers={"host": "avascry.com"})
        assert res.status_code == 200
        assert "adsbygoogle.js" not in res.text, f"adsbygoogle.js unexpectedly found on {path}"
