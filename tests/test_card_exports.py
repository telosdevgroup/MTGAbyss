import os
import sys
import io
import csv
import xml.etree.ElementTree as ET
import pytest
from starlette.testclient import TestClient

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_printing_json_has_xml_and_csv_links(client):
    response = client.get("/printing/black-lotus-lea.json")
    assert response.status_code == 200
    data = response.json()
    assert "links" in data
    links = data["links"]
    assert "json" in links
    assert "markdown" in links
    assert "xml" in links
    assert "csv" in links
    assert links["xml"].endswith(".xml")
    assert links["csv"].endswith(".csv")

def test_printing_xml_cockatrice_format(client):
    response = client.get("/printing/black-lotus-lea.xml")
    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")
    
    # Parse XML and verify Cockatrice v4 schema
    root = ET.fromstring(response.content)
    assert root.tag == "cockatrice_carddatabase"
    assert root.get("version") == "4"
    
    sets_elem = root.find("sets")
    assert sets_elem is not None
    set_elem = sets_elem.find("set")
    assert set_elem is not None
    assert set_elem.find("name").text == "LEA"
    
    cards_elem = root.find("cards")
    assert cards_elem is not None
    card_elem = cards_elem.find("card")
    assert card_elem is not None
    assert card_elem.find("name").text == "Black Lotus"
    assert card_elem.find("prop") is not None
    assert card_elem.find("prop").find("type") is not None

def test_printing_csv_format(client):
    response = client.get("/printing/black-lotus-lea.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    
    reader = list(csv.reader(io.StringIO(response.text)))
    assert len(reader) >= 2  # header + 1 data row
    header = reader[0]
    assert "name" in header
    assert "set" in header
    assert "collector_number" in header
    assert "oracle_text" in header
    
    row = reader[1]
    name_idx = header.index("name")
    set_idx = header.index("set")
    assert row[name_idx] == "Black Lotus"
    assert row[set_idx] == "LEA"

def test_alternate_link_headers(client):
    response = client.get("/printing/black-lotus-lea")
    assert response.status_code == 200
    link_header = response.headers.get("link", "")
    assert 'rel="alternate"' in link_header
    assert 'type="text/markdown"' in link_header
    assert 'type="application/json"' in link_header
    assert 'type="application/xml"' in link_header
    assert 'type="text/csv"' in link_header

def test_query_param_format_xml_and_csv(client):
    res_xml = client.get("/printing/black-lotus-lea?format=xml")
    assert res_xml.status_code == 200
    assert "application/xml" in res_xml.headers.get("content-type", "")
    assert b"cockatrice_carddatabase" in res_xml.content

    res_csv = client.get("/printing/black-lotus-lea?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")
    assert "Black Lotus" in res_csv.text

def test_card_shortcut_redirects_with_format(client):
    res = client.get("/card/black-lotus.xml", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/printing/black-lotus-lea.xml"

    res_csv = client.get("/card/black-lotus.csv", follow_redirects=False)
    assert res_csv.status_code == 303
    assert res_csv.headers["location"] == "/printing/black-lotus-lea.csv"

def test_head_requests_for_xml_and_csv(client):
    head_xml = client.head("/printing/black-lotus-lea.xml")
    assert head_xml.status_code == 200
    assert "application/xml" in head_xml.headers.get("content-type", "")

    head_csv = client.head("/printing/black-lotus-lea.csv")
    assert head_csv.status_code == 200
    assert "text/csv" in head_csv.headers.get("content-type", "")

def test_html_page_contains_alternate_links_and_export_button(client):
    res = client.get("/printing/black-lotus-lea")
    assert res.status_code == 200
    html = res.text
    # Verify alternate link discovery in <head>
    assert '<link rel="alternate" type="application/json"' in html
    assert '<link rel="alternate" type="application/xml"' in html
    assert '<link rel="alternate" type="text/csv"' in html
    assert '<link rel="alternate" type="text/markdown"' in html
    # Verify Export UI dropdown and formats
    assert 'id="btn-export-dropdown"' in html
    assert 'id="export-dropdown-menu"' in html
    assert '/printing/black-lotus-lea.json' in html
    assert '/printing/black-lotus-lea.md' in html
    assert '/printing/black-lotus-lea.xml' in html
    assert '/printing/black-lotus-lea.csv' in html

