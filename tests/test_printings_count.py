import os
import sys
import re
import pytest
from starlette.testclient import TestClient

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db_mongo import get_mongo_db

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="module")
def db():
    return get_mongo_db()

# Representative sample of cards with diverse printing counts:
# 1. Single/few printings English only (e.g. Unfinity cards)
# 2. Iconic multi-printings across decades
# 3. Modern staples
# 4. Multilingual printings
SAMPLE_TEST_SLUGS = [
    "black-lotus-lea",
    "lightning-bolt-lea",
    "dark-confidant-rav",
    "thoughtseize-lrw",
    "birds-of-paradise-lea",
    "sol-ring-lea",
    "animate-object-unf",
    "scavenging-ghoul-c15-ja"
]

def get_actual_db_printings_count(db, oracle_id: str) -> int:
    """Helper to query the exact count of printings stored in card_prints / cards."""
    count = db["card_prints"].count_documents({"oracle_id": oracle_id})
    if count == 0:
        count = db["cards"].count_documents({"oracle_id": oracle_id})
    return count

@pytest.mark.parametrize("slug", SAMPLE_TEST_SLUGS)
def test_printings_count_matches_db_and_json_api(client, db, slug):
    """Verify that the JSON API endpoint returns the exact printings_count matching MongoDB."""
    # Find card to obtain oracle_id
    res_json = client.get(f"/printing/{slug}.json")
    if res_json.status_code == 404:
        pytest.skip(f"Card {slug} not found in database.")

    assert res_json.status_code == 200
    data = res_json.json()
    oracle_id = data.get("oracle_id")
    assert oracle_id, f"Missing oracle_id in JSON output for {slug}"

    expected_db_count = get_actual_db_printings_count(db, oracle_id)
    api_printings_count = data.get("printings_count")

    assert api_printings_count == expected_db_count, (
        f"Mismatch for {slug} (oracle_id: {oracle_id}): "
        f"API returned {api_printings_count}, DB has {expected_db_count}"
    )

@pytest.mark.parametrize("slug", SAMPLE_TEST_SLUGS)
def test_printings_count_in_html_accordion(client, db, slug):
    """Verify that the rendered HTML accordion header and language rows sum up to the exact DB count."""
    res_json = client.get(f"/printing/{slug}.json")
    if res_json.status_code == 404:
        pytest.skip(f"Card {slug} not found in database.")

    assert res_json.status_code == 200
    oracle_id = res_json.json().get("oracle_id")
    expected_db_count = get_actual_db_printings_count(db, oracle_id)

    res_html = client.get(f"/printing/{slug}")
    assert res_html.status_code == 200
    html_text = res_html.text

    # 1. Verify accordion header total: e.g. "(24)" inside panel-title
    m_header_count = re.search(r'class="panel-title"[^>]*>[^<(]*\((\d+)\)</span>', html_text)
    assert m_header_count, f"Could not find historical printings header count in HTML for {slug}"
    header_count = int(m_header_count.group(1))

    assert header_count == expected_db_count, (
        f"HTML header count ({header_count}) does not match DB count ({expected_db_count}) for {slug}"
    )

    # 2. Verify table rows rendered across all language accordions sum to expected_db_count
    # Each printing renders as a <tr class="printing-row-item ...">
    rendered_table_rows = len(re.findall(r'class="printing-row-item', html_text))
    assert rendered_table_rows == expected_db_count, (
        f"Sum of rendered table rows ({rendered_table_rows}) does not match DB count ({expected_db_count}) for {slug}"
    )

@pytest.mark.parametrize("slug", SAMPLE_TEST_SLUGS)
def test_printings_count_in_markdown_export(client, db, slug):
    """Verify that the markdown representation has the exact number of printings in the markdown table."""
    res_json = client.get(f"/printing/{slug}.json")
    if res_json.status_code == 404:
        pytest.skip(f"Card {slug} not found in database.")

    assert res_json.status_code == 200
    oracle_id = res_json.json().get("oracle_id")
    expected_db_count = get_actual_db_printings_count(db, oracle_id)

    res_md = client.get(f"/printing/{slug}.md")
    assert res_md.status_code == 200
    md_text = res_md.text

    # Markdown frontmatter has printings_count: X
    m_fm = re.search(r'printings_count:\s*(\d+)', md_text)
    assert m_fm, f"Missing printings_count in markdown frontmatter for {slug}"
    md_count = int(m_fm.group(1))

    assert md_count == expected_db_count, (
        f"Markdown count ({md_count}) does not match DB count ({expected_db_count}) for {slug}"
    )

if __name__ == "__main__":
    test_client = TestClient(app)
    db_conn = get_mongo_db()
    passed = 0
    total = 0

    print("=" * 60)
    print("RUNNING PRINTINGS COUNT VERIFICATION TESTS")
    print("=" * 60)

    for slug in SAMPLE_TEST_SLUGS:
        total += 1
        print(f"\n[TESTING] {slug}...")
        try:
            test_printings_count_matches_db_and_json_api(test_client, db_conn, slug)
            test_printings_count_in_html_accordion(test_client, db_conn, slug)
            test_printings_count_in_markdown_export(test_client, db_conn, slug)
            
            # Fetch and print verified counts
            res_json = test_client.get(f"/printing/{slug}.json")
            data = res_json.json()
            oid = data.get("oracle_id")
            count = get_actual_db_printings_count(db_conn, oid)
            print(f"  [PASS] Oracle ID {oid[:8]}... has exactly {count} printings across DB, HTML, JSON, and Markdown.")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {slug} -> {e}")

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed}/{total} PASSED")
    print("=" * 60)
    if passed != total:
        sys.exit(1)
