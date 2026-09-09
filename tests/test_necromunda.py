from starlette.testclient import TestClient
from app import app

client = TestClient(app)

def test_necromunda_endpoints():
    # 1. Test prefix routes
    r = client.get('/necromunda')
    assert r.status_code == 200, f"/necromunda returned {r.status_code}"
    assert 'Underhive Armory' in r.text
    assert 'Skill Disciplines &amp; Upgrades' in r.text or 'Skill Disciplines & Upgrades' in r.text

    r = client.get('/necromunda/weapons')
    assert r.status_code == 200
    assert 'heavy-bolter' in r.text.lower() or 'heavy bolter' in r.text.lower()

    r = client.get('/necromunda/weapon/heavy-bolter')
    assert r.status_code == 200
    assert 'heavy bolter' in r.text.lower()

    r = client.get('/necromunda/weapon/heavy-bolter.md')
    assert r.status_code == 200
    assert 'heavy bolter' in r.text.lower()
    assert 'slug: "heavy-bolter"' in r.text

    r = client.get('/necromunda/weapon/heavy-bolter.json')
    assert r.status_code == 200
    assert r.json()['cost_credits'] == 160

    # 2. Test traits
    r = client.get('/necromunda/traits')
    assert r.status_code == 200
    assert 'id="traitFilterInput"' in r.text
    assert 'id="traitCategoryPillRow"' in r.text
    assert 'data-cat="all"' in r.text
    r = client.get('/necromunda/trait/rapid-fire-1')
    assert r.status_code == 200
    r = client.get('/necromunda/trait/rapid-fire-1.md')
    assert r.status_code == 200
    r = client.get('/necromunda/trait/rapid-fire-1.json')
    assert r.status_code == 200

    # 3. Test houses
    r = client.get('/necromunda/houses')
    assert r.status_code == 200
    assert 'id="houseFilterInput"' in r.text
    assert 'house-card' in r.text
    r = client.get('/necromunda/house/van-saar')
    assert r.status_code == 200
    r = client.get('/necromunda/house/van-saar.md')
    assert r.status_code == 200
    r = client.get('/necromunda/house/van-saar.json')
    assert r.status_code == 200

    # 4. Test skills
    r = client.get('/necromunda/skills')
    assert r.status_code == 200
    assert 'id="skillFilterInput"' in r.text
    assert 'id="skillTreePillRow"' in r.text
    assert 'data-cat="all"' in r.text
    r = client.get('/necromunda/skill/fast-shot')
    assert r.status_code == 200
    r = client.get('/necromunda/skill/fast-shot.md')
    assert r.status_code == 200
    r = client.get('/necromunda/skill/fast-shot.json')
    assert r.status_code == 200

    # 5. Test llms.txt & sitemap
    r = client.get('/necromunda/llms.txt')
    assert r.status_code == 200
    r = client.get('/necromunda/llms-full.txt')
    assert r.status_code == 200
    assert 'AvaScry Necromunda' in r.text
    r = client.get('/necromunda/sitemap.xml')
    assert r.status_code == 200
    assert '<loc>https://necromunda.avascry.com/weapon/' in r.text

    # 6. Test HTML & Markdown Sitemaps
    r = client.get('/necromunda/sitemap.html')
    assert r.status_code == 200
    assert 'Underhive Lexicon &amp; Armory Sitemap' in r.text or 'Underhive Lexicon & Armory Sitemap' in r.text
    assert 'badge-md' in r.text
    assert 'heavy bolter' in r.text.lower() or 'heavy-bolter' in r.text.lower()

    r = client.get('/necromunda/sitemap.md')
    assert r.status_code == 200
    assert '# AvaScry Necromunda — Master Sitemap' in r.text
    assert 'https://necromunda.avascry.com/weapon/heavy-bolter.md' in r.text

    # 7. Test Subdomain Host Routing
    r = client.get('/', headers={'host': 'necromunda.avascry.com'})
    assert r.status_code == 200
    assert 'Underhive Armory' in r.text

    r = client.get('/sitemap.html', headers={'host': 'necromunda.avascry.com'})
    assert r.status_code == 200
    assert 'Underhive Lexicon' in r.text

    r = client.get('/sitemap.md', headers={'host': 'necromunda.avascry.com'})
    assert r.status_code == 200
    assert '# AvaScry Necromunda' in r.text

    r = client.get('/weapon/heavy-bolter.json', headers={'host': 'necromunda.avascry.com'})
    assert r.status_code == 200
    assert r.json()['cost_credits'] == 160

    # 8. Test Legal & Support Endpoints (AdSense compliance & Contact Webhook)
    r = client.get('/necromunda/about')
    assert r.status_code == 200
    assert 'About AvaScry Necromunda' in r.text

    r = client.get('/necromunda/privacy')
    assert r.status_code == 200
    assert 'Privacy Policy' in r.text
    assert 'Google AdSense' in r.text

    r = client.get('/necromunda/terms')
    assert r.status_code == 200
    assert 'Terms of Service' in r.text

    r = client.get('/necromunda/contact')
    assert r.status_code == 200
    assert 'Contact' in r.text

    # Contact POST with valid data (mocked to avoid spamming the live webhook during tests)
    from unittest.mock import patch, AsyncMock
    with patch('mtgabyss.routers.auth_router.send_discord_notification', new_callable=AsyncMock) as mock_notify:
        r = client.post('/necromunda/contact', data={
            'name': 'Alex',
            'contact': 'alex@example.com',
            'message': 'Testing feedback submission.'
        })
        assert r.status_code == 200
        assert 'Message Sent!' in r.text
        assert mock_notify.called
        assert mock_notify.call_args.kwargs['fields'][1]['value'] == 'Alex'

    # Contact POST honeypot spam protection
    r = client.post('/necromunda/contact', data={
        'website_url': 'http://spambot.com',
        'name': 'Bot',
        'contact': 'bot@spam.com',
        'message': 'Spam payload'
    })
    assert r.status_code == 200
    assert 'Message Sent!' in r.text

    # Contact POST validation failure
    r = client.post('/necromunda/contact', data={
        'name': '',
        'contact': '',
        'message': ''
    })
    assert r.status_code == 200
    assert 'Please provide your contact info and a message.' in r.text

    # Subdomain legal endpoints
    r = client.get('/privacy', headers={'host': 'necromunda.avascry.com'})
    assert r.status_code == 200
    assert 'Google AdSense' in r.text

    # Subdomain robots.txt crawler endpoint
    r_rob = client.get('/robots.txt', headers={'host': 'necromunda.avascry.com'})
    assert r_rob.status_code == 200
    assert 'Googlebot' in r_rob.text
    assert 'https://necromunda.avascry.com/sitemap.xml' in r_rob.text
    assert 'https://necromunda.avascry.com/sitemap.md' in r_rob.text

    print("ALL NARROW TESTS PASSED!")

if __name__ == "__main__":
    test_necromunda_endpoints()

