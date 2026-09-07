import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from db_mongo import get_mongo_db

class TestVisualSimilarityRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = get_mongo_db()
        cls.known_ill_id = "d5de278d-bea6-456e-bf89-ed701e5de7a5"  # Shalai and Hallar (moc)
        cls.known_slug = "shalai-and-hallar-moc"

    def test_01_printing_with_no_vl_record_renders_normally(self):
        """Cards with no VL record must render HTML, JSON, and MD without any errors."""
        analyzed_ids = set(self.db.vl_art_analysis.distinct("illustration_id"))
        unassigned_card = self.db.cards.find_one({
            "lang": "en",
            "slug": {"$exists": True, "$ne": None, "$ne": ""},
            "illustration_id": {"$nin": list(analyzed_ids)[:1000]}
        })
        self.assertIsNotNone(unassigned_card, "Could not find unassigned card")
        target_slug = unassigned_card.get("printing_slug") or unassigned_card.get("slug")

        res_html = self.client.get(f"/printing/{target_slug}")
        self.assertEqual(res_html.status_code, 200)
        self.assertNotIn("Visually Similar Art", res_html.text)

        res_json = self.client.get(f"/printing/{target_slug}.json")
        self.assertEqual(res_json.status_code, 200)
        self.assertIsNone(res_json.json().get("visual_artwork"))

        res_md = self.client.get(f"/printing/{target_slug}.md")
        self.assertEqual(res_md.status_code, 200)
        self.assertNotIn("## Visual Art Observations", res_md.text)

    def test_02_illustration_with_vl_but_no_similarity_record(self):
        """A card with VL analysis but no similarity profile must render without crashing."""
        mock_id = "test-mock-vl-only-id-9999"
        self.db.vl_art_analysis.update_one(
            {"illustration_id": mock_id},
            {"$set": {
                "illustration_id": mock_id,
                "status": "complete",
                "vision_observations": {
                    "visual_summary": "A lone monolith in a desolate tundra.",
                    "subjects": ["monolith"],
                    "setting": ["tundra"],
                    "dominant_colors": ["grey", "white"],
                    "style_descriptors": ["minimalist", "high-contrast"],
                    "mood_keywords": ["somber", "serene"]
                }
            }},
            upsert=True
        )
        try:
            res_json = self.client.get(f"/art/{mock_id}.json")
            self.assertEqual(res_json.status_code, 200)
            data = res_json.json()
            self.assertEqual(data["vision_observations"]["visual_summary"], "A lone monolith in a desolate tundra.")
            for cat in ["by_subject", "by_vibe", "by_scene"]:
                self.assertEqual(data["top_neighbors"].get(cat), [])

            res_md = self.client.get(f"/art/{mock_id}.md")
            self.assertEqual(res_md.status_code, 200)
            self.assertIn("A lone monolith in a desolate tundra.", res_md.text)
            self.assertNotIn("## Top 7 Nearest Visual Neighbors", res_md.text)
        finally:
            self.db.vl_art_analysis.delete_one({"illustration_id": mock_id})

    def test_03_neighbor_never_returns_itself(self):
        """Top 7 nearest neighbors must never include the target illustration itself."""
        sim_doc = self.db.vl_art_similarities.find_one({"illustration_id": self.known_ill_id})
        self.assertIsNotNone(sim_doc)
        top_n = sim_doc.get("top_neighbors", {})
        for category in ["by_subject", "by_vibe", "by_scene"]:
            neighbors = top_n.get(category, [])
            neighbor_ids = [n.get("illustration_id") for n in neighbors]
            self.assertNotIn(self.known_ill_id, neighbor_ids, f"Self-referential neighbor found in {category}")
            self.assertEqual(len(neighbors), 7, f"Expected exactly 7 neighbors in {category}")

    def test_04_no_percent_match_in_any_output(self):
        """Strict grounding: No '% match' or 'visual match' in UI, JSON, or Markdown."""
        # 1. Art JSON
        res_art_json = self.client.get(f"/art/{self.known_ill_id}.json")
        self.assertNotIn("%", res_art_json.text)
        self.assertNotIn("match_pct", res_art_json.text)

        # 2. Art Markdown
        res_art_md = self.client.get(f"/art/{self.known_ill_id}.md")
        self.assertNotIn("% match", res_art_md.text)
        self.assertNotIn("visual match", res_art_md.text)

        # 3. Printing JSON
        res_card_json = self.client.get(f"/printing/{self.known_slug}.json")
        self.assertNotIn("match_pct", res_card_json.text)

        # 4. Printing Markdown
        res_card_md = self.client.get(f"/printing/{self.known_slug}.md")
        self.assertNotIn("% match", res_card_md.text)
        self.assertNotIn("visual match", res_card_md.text)

        # 5. HTML Gallery
        res_html = self.client.get(f"/printing/{self.known_slug}")
        self.assertNotIn("% match", res_html.text)
        self.assertNotIn("match_pct", res_html.text)

    def test_05_schema_visual_artwork_has_no_art_medium(self):
        """Schema.org VisualArtwork must NEVER infer artMedium from style_descriptors."""
        res_html = self.client.get(f"/printing/{self.known_slug}")
        self.assertEqual(res_html.status_code, 200)
        self.assertNotIn('"artMedium"', res_html.text)
        self.assertIn('"VisualArtwork"', res_html.text)
        self.assertIn('"Visual Style Descriptor"', res_html.text)
        self.assertIn('"Atmospheric Mood"', res_html.text)

    def test_06_json_md_html_illustration_id_consistency(self):
        """HTML, JSON, and MD must resolve to the identical illustration ID and Link headers."""
        res_json = self.client.get(f"/printing/{self.known_slug}.json")
        res_md = self.client.get(f"/printing/{self.known_slug}.md")
        res_html = self.client.get(f"/printing/{self.known_slug}")

        json_ill_id = res_json.json().get("visual_artwork", {}).get("illustration_id")
        self.assertEqual(json_ill_id, self.known_ill_id)

        # Header links agreement
        for res in [res_json, res_md, res_html]:
            link_header = res.headers.get("link", "")
            self.assertIn(f"/art/{self.known_ill_id}.json", link_header)
            self.assertIn(f"/art/{self.known_ill_id}.md", link_header)

    def test_07_unicode_survives_link_headers(self):
        """Unicode characters in slugs/cards must not crash HTTP Link header construction."""
        card = self.db.cards.find_one({"name": {"$regex": "[\u0080-\uffff]"}, "slug": {"$exists": True, "$ne": None, "$ne": ""}})
        if card:
            target_slug = card.get("printing_slug") or card.get("slug")
            res = self.client.get(f"/printing/{target_slug}")
            self.assertIn(res.status_code, [200, 301, 302, 303])
            # Headers must be valid Latin-1 / ASCII safe
            for k, v in res.headers.items():
                v.encode("latin-1")
    def test_08_placeholder_images_filtered_and_rejected(self):
        """Cards with image_status placeholder or missing must be rejected to prevent compute waste."""
        from tasks import _extract_card_art_info

        # 1. Reject placeholder
        placeholder_card = {
            "name": "Test Placeholder Card",
            "lang": "pt",
            "image_status": "placeholder",
            "image_uris": {"art_crop": "https://cards.scryfall.io/art_crop/front/0/0/dummy.jpg"},
            "illustration_id": "dummy-placeholder-id"
        }
        img_url, meta = _extract_card_art_info(placeholder_card)
        self.assertIsNone(img_url)
        self.assertIsNone(meta)

        # 2. Reject missing
        missing_card = {
            "name": "Test Missing Card",
            "lang": "en",
            "image_status": "missing",
            "image_uris": {"art_crop": "https://cards.scryfall.io/art_crop/front/0/0/dummy2.jpg"},
            "illustration_id": "dummy-missing-id"
        }
        img_url2, meta2 = _extract_card_art_info(missing_card)
        self.assertIsNone(img_url2)
        self.assertIsNone(meta2)

        # 3. Accept valid highres scan
        valid_card = {
            "name": "Test Valid Card",
            "lang": "en",
            "image_status": "highres_scan",
            "image_uris": {"art_crop": "https://cards.scryfall.io/art_crop/front/0/0/clean.jpg"},
            "illustration_id": "clean-id",
            "artist": "Test Artist",
            "set": "lea"
        }
        img_url3, meta3 = _extract_card_art_info(valid_card)
        self.assertEqual(img_url3, "https://cards.scryfall.io/art_crop/front/0/0/clean.jpg")
        self.assertIsNotNone(meta3)
        self.assertEqual(meta3["card_name"], "Test Valid Card")

if __name__ == "__main__":
    unittest.main()
