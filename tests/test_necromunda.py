from starlette.testclient import TestClient
from app import app

client = TestClient(app)

def test_necromunda_endpoints():
    # 1. Test prefix routes
    r = client.get('/necromunda')
    assert r.status_code == 200, f"/necromunda returned {r.status_code}"
    assert 'Underhive Armory' in r.text

    r = client.get('/necromunda/weapons')
    assert r.status_code == 200
    assert 'Heavy Bolter' in r.text

    r = client.get('/necromunda/weapon/heavy-bolter')
    assert r.status_code == 200
    assert 'Heavy Bolter' in r.text

    r = client.get('/necromunda/weapon/heavy-bolter.md')
    assert r.status_code == 200
    assert '# Heavy Bolter' in r.text
    assert 'slug: "heavy-bolter"' in r.text

    r = client.get('/necromunda/weapon/heavy-bolter.json')
    assert r.status_code == 200
    assert r.json()['cost_credits'] == 160

    # 2. Test traits
    r = client.get('/necromunda/traits')
    assert r.status_code == 200
    r = client.get('/necromunda/trait/rapid-fire-1')
    assert r.status_code == 200
    r = client.get('/necromunda/trait/rapid-fire-1.md')
    assert r.status_code == 200
    r = client.get('/necromunda/trait/rapid-fire-1.json')
    assert r.status_code == 200

    # 3. Test houses
    r = client.get('/necromunda/houses')
    assert r.status_code == 200
    r = client.get('/necromunda/house/van-saar')
    assert r.status_code == 200
    r = client.get('/necromunda/house/van-saar.md')
    assert r.status_code == 200
    r = client.get('/necromunda/house/van-saar.json')
    assert r.status_code == 200

    # 4. Test skills
    r = client.get('/necromunda/skills')
    assert r.status_code == 200
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
    assert '<loc>https://necromunda.avascry.com/weapon/heavy-bolter</loc>' in r.text

    # 6. Test Subdomain Host Routing
    r = client.get('/', headers={'host': 'necromunda.avascry.com'})
    assert r.status_code == 200
    assert 'Underhive Armory' in r.text

    r = client.get('/weapon/heavy-bolter.json', headers={'host': 'necromunda.avascry.com'})
    assert r.status_code == 200
    assert r.json()['cost_credits'] == 160

    print("ALL 16 NARROW TESTS PASSED!")

if __name__ == "__main__":
    test_necromunda_endpoints()
