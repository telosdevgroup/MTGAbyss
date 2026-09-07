#!/usr/bin/env python3
"""
scripts/submit_indexnow.py
--------------------------
Submits canonical URLs for Star Wars: Unlimited (SWU), Necromunda, and Dominion
to the IndexNow REST API (Bing / Yandex indexing network).
"""
import os
import sys
import httpx

INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b3901b0f58d0445bb8d15a9e334df58a")
INDEXNOW_ENDPOINTS = [
    "https://www.bing.com/indexnow",
    "https://yandex.com/indexnow",
]

# Curated canonical URL batches for the primary domain avascry.com
AVASCRY_URLS = [
    # --- NECROMUNDA ---
    "https://avascry.com/necromunda",
    "https://avascry.com/necromunda/weapons",
    "https://avascry.com/necromunda/traits",
    "https://avascry.com/necromunda/houses",
    "https://avascry.com/necromunda/skills",
    "https://avascry.com/necromunda/sitemap.xml",
    "https://avascry.com/necromunda/llms.txt",
    "https://avascry.com/necromunda/llms-full.txt",
    "https://avascry.com/necromunda/weapon/heavy-bolter",
    "https://avascry.com/necromunda/weapon/heavy-bolter.md",
    "https://avascry.com/necromunda/weapon/heavy-bolter.json",
    "https://avascry.com/necromunda/weapon/autogun",
    "https://avascry.com/necromunda/weapon/chainsword",
    "https://avascry.com/necromunda/weapon/plasma-gun",
    "https://avascry.com/necromunda/weapon/meltagun",
    "https://avascry.com/necromunda/weapon/lasgun",
    "https://avascry.com/necromunda/weapon/fighting-knife",
    "https://avascry.com/necromunda/house/van-saar",
    "https://avascry.com/necromunda/house/van-saar.md",
    "https://avascry.com/necromunda/house/van-saar.json",
    "https://avascry.com/necromunda/house/goliath",
    "https://avascry.com/necromunda/house/escher",
    "https://avascry.com/necromunda/house/orlock",
    "https://avascry.com/necromunda/house/cawdor",
    "https://avascry.com/necromunda/house/delaque",
    "https://avascry.com/necromunda/house/palanite-enforcers",
    "https://avascry.com/necromunda/trait/rapid-fire-1",
    "https://avascry.com/necromunda/trait/blaze",
    "https://avascry.com/necromunda/trait/seismic",
    "https://avascry.com/necromunda/skill/fast-shot",
    "https://avascry.com/necromunda/skill/infiltrate",

    # --- STAR WARS: UNLIMITED ---
    "https://avascry.com/swu",
    "https://avascry.com/swu/cards",
    "https://avascry.com/swu/sets",
    "https://avascry.com/swu/llms.txt",
    "https://avascry.com/swu/llms-full.txt",

    # --- DOMINION ---
    "https://avascry.com/dominion",
    "https://avascry.com/dominion/cards",
    "https://avascry.com/dominion/sets",
    "https://avascry.com/dominion/kingdoms",
]

SUBDOMAINS = [
    {
        "host": "necromunda.avascry.com",
        "urls": [
            "https://necromunda.avascry.com/",
            "https://necromunda.avascry.com/weapons",
            "https://necromunda.avascry.com/traits",
            "https://necromunda.avascry.com/houses",
            "https://necromunda.avascry.com/skills",
            "https://necromunda.avascry.com/sitemap.xml",
            "https://necromunda.avascry.com/llms.txt",
            "https://necromunda.avascry.com/weapon/heavy-bolter",
            "https://necromunda.avascry.com/weapon/autogun",
            "https://necromunda.avascry.com/weapon/chainsword",
            "https://necromunda.avascry.com/house/van-saar",
            "https://necromunda.avascry.com/house/goliath",
            "https://necromunda.avascry.com/house/escher",
            "https://necromunda.avascry.com/house/delaque",
            "https://necromunda.avascry.com/trait/rapid-fire-1",
            "https://necromunda.avascry.com/skill/fast-shot",
        ]
    },
    {
        "host": "swu.avascry.com",
        "urls": [
            "https://swu.avascry.com/",
            "https://swu.avascry.com/cards",
            "https://swu.avascry.com/sets",
            "https://swu.avascry.com/llms.txt",
        ]
    },
    {
        "host": "dominion.avascry.com",
        "urls": [
            "https://dominion.avascry.com/",
            "https://dominion.avascry.com/cards",
            "https://dominion.avascry.com/sets",
            "https://dominion.avascry.com/kingdoms",
        ]
    }
]


def submit_batch(host: str, urls: list):
    payload = {
        "host": host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{host}/{INDEXNOW_KEY}.txt",
        "urlList": urls
    }
    print(f"\nSubmitting {len(urls)} URLs for host '{host}'...")
    for ep in INDEXNOW_ENDPOINTS:
        try:
            with httpx.Client(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                resp = client.post(ep, json=payload)
                status_desc = "SUCCESS" if resp.status_code in (200, 202) else "NOTICE"
                print(f"[{host} -> {ep}] HTTP {resp.status_code} ({status_desc})")
        except Exception as e:
            print(f"[{host} -> {ep}] Error: {e}")


def main():
    print("=== IndexNow API Submitter ===")
    print(f"Endpoints: {', '.join(INDEXNOW_ENDPOINTS)}")
    print(f"Key: {INDEXNOW_KEY}")

    # 1. Primary avascry.com batch
    submit_batch("avascry.com", AVASCRY_URLS)

    # 2. Subdomain batches
    for sub in SUBDOMAINS:
        submit_batch(sub["host"], sub["urls"])

    print("\nAll IndexNow batches dispatched.")


if __name__ == "__main__":
    main()
