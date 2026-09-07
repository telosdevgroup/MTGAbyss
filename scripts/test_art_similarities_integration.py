import os
import sys
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app

def run_tests():
    client = TestClient(app)
    known_illustration_id = "d5de278d-bea6-456e-bf89-ed701e5de7a5"  # Shalai and Hallar (moc)
    known_card_slug = "shalai-and-hallar-moc"

    print(f"[*] Testing /art/{known_illustration_id}.json...")
    res = client.get(f"/art/{known_illustration_id}.json")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["illustration_id"] == known_illustration_id, "illustration_id mismatch"
    assert "top_neighbors" in data, "top_neighbors missing"
    assert len(data["top_neighbors"]["by_subject"]) == 7, f"Expected 7 subject neighbors, got {len(data['top_neighbors']['by_subject'])}"
    assert len(data["top_neighbors"]["by_vibe"]) == 7, f"Expected 7 vibe neighbors, got {len(data['top_neighbors']['by_vibe'])}"
    assert len(data["top_neighbors"]["by_scene"]) == 7, f"Expected 7 scene neighbors, got {len(data['top_neighbors']['by_scene'])}"
    assert "visual_summary" in data["vision_observations"], "visual_summary missing"
    print("    [PASS] /art/{id}.json returns complete vision observations and 7 lucky neighbors across all 3 facets.")

    print(f"[*] Testing /art/{known_illustration_id}.md...")
    res_md = client.get(f"/art/{known_illustration_id}.md")
    assert res_md.status_code == 200, f"Expected 200, got {res_md.status_code}"
    assert "Visual Artwork Analysis:" in res_md.text, "Header missing in markdown"
    assert "## Top 7 Nearest Visual Neighbors" in res_md.text, "Neighbor section missing in markdown"
    assert "By Subject & Entities" in res_md.text, "Subject facet missing"
    print("    [PASS] /art/{id}.md returns structured LLM markdown report.")

    print(f"[*] Testing /printing/{known_card_slug}.json...")
    res_card_json = client.get(f"/printing/{known_card_slug}.json")
    assert res_card_json.status_code == 200, f"Expected 200, got {res_card_json.status_code}"
    card_data = res_card_json.json()
    assert "visual_artwork" in card_data, "visual_artwork key missing in card json"
    assert card_data["visual_artwork"]["illustration_id"] == known_illustration_id
    assert len(card_data["visual_artwork"]["top_neighbors"]["by_subject"]) == 7
    print("    [PASS] /printing/{slug}.json includes visual_artwork payload with 7 neighbors.")

    print(f"[*] Testing /printing/{known_card_slug}.md...")
    res_card_md = client.get(f"/printing/{known_card_slug}.md")
    assert res_card_md.status_code == 200, f"Expected 200, got {res_card_md.status_code}"
    assert "## Visual Art Observations (Qwen3-VL 8B)" in res_card_md.text
    assert "## Top 7 Nearest Visual Neighbors" in res_card_md.text
    print("    [PASS] /printing/{slug}.md includes visual art observations & top 7 neighbors.")

    print(f"[*] Testing HTML page /printing/{known_card_slug}...")
    res_html = client.get(f"/printing/{known_card_slug}")
    assert res_html.status_code == 200, f"Expected 200, got {res_html.status_code}"
    html_text = res_html.text
    assert "Visually Similar Art" in html_text, "'Visually Similar Art' missing in HTML"
    assert "Lucky 7" not in html_text, "Lucky 7 jargon still in HTML"
    assert "Neural Neighbors" not in html_text, "Neural Neighbors jargon still in HTML"
    assert "VisualArtwork" in html_text, "Schema.org VisualArtwork missing in HTML"
    assert "btn-art-subject" in html_text, "Tab button missing"
    assert "JSON API" in html_text, "Bottom JSON link missing"
    print("    [PASS] HTML card page renders large human-centric Visually Similar Art gallery.")

    print("\n[SUCCESS] All visual similarity and SELLMO art integration tests passed perfectly!")

if __name__ == "__main__":
    run_tests()
