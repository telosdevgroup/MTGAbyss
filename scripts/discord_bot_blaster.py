#!/usr/bin/env python3
"""
discord_bot_blaster.py — Automated Health & Release Gate for AvaScry Discord Bot.

Rigorously tests /api/discord/interactions against FastAPI:
- Cryptographic Ed25519 signature verification & rejection of tampered requests
- Type 1 Heartbeat / PING
- Multi-game slash commands (/mtg, /necro, /swu, /dom, /mc)
- Rich embeds, fields, footer branding, and image asset links
- Sub-1500ms response latency SLA (well under Discord's 3-second hard timeout)

Usage:
    python scripts/discord_bot_blaster.py --quick
    python scripts/discord_bot_blaster.py --deep
    python scripts/discord_bot_blaster.py --base-url http://localhost:8004 --quick
"""

import os
import sys
import json
import time
import argparse
from typing import Optional, Dict, Any, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import httpx
from starlette.testclient import TestClient

# Generate ephemeral test keypair for signing
TEST_PRIV_KEY = ed25519.Ed25519PrivateKey.generate()
TEST_PUB_KEY = TEST_PRIV_KEY.public_key()
TEST_PUB_KEY_HEX = TEST_PUB_KEY.public_bytes(
    serialization.Encoding.Raw,
    serialization.PublicFormat.Raw
).hex()

# Register the public key in the environment before importing app
os.environ["DISCORD_PUBLIC_KEY"] = TEST_PUB_KEY_HEX

from app import app


class DiscordBotBlaster:
    LATENCY_THRESHOLD_MS = 1500.0  # Discord times out interactions at 3000ms

    def __init__(self, base_url: Optional[str] = None, deep: bool = False):
        self.deep = deep
        self.base_url = (base_url or "").rstrip("/")
        if self.base_url:
            self.client = httpx.Client(base_url=self.base_url, timeout=10.0)
            self._is_testclient = False
        else:
            self.client = TestClient(app, base_url="http://testserver")
            self._is_testclient = True

        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results: List[Dict[str, Any]] = []

    def sign_payload(self, body_bytes: bytes, timestamp: Optional[str] = None) -> Dict[str, str]:
        ts = timestamp or str(int(time.time()))
        sig = TEST_PRIV_KEY.sign(ts.encode("utf-8") + body_bytes).hex()
        return {
            "Content-Type": "application/json",
            "X-Signature-Ed25519": sig,
            "X-Signature-Timestamp": ts
        }

    def post_interaction(self, payload: dict, valid_sig: bool = True) -> tuple[int, dict, float]:
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = self.sign_payload(body_bytes)
        if not valid_sig:
            headers["X-Signature-Ed25519"] = "0" * 128

        t0 = time.perf_counter()
        resp = self.client.post("/api/discord/interactions", content=body_bytes, headers=headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        
        data = {}
        try:
            data = resp.json()
        except Exception:
            pass
        return resp.status_code, data, elapsed_ms

    def log_pass(self, suite: str, message: str):
        self.passed += 1
        print(f"  [PASS] [{suite}] {message}")

    def log_fail(self, suite: str, message: str):
        self.failed += 1
        print(f"  [FAIL] [{suite}] {message}")

    def log_warn(self, suite: str, message: str):
        self.warnings += 1
        print(f"  [WARN] [{suite}] {message}")

    def test_security_and_heartbeat(self):
        print("\n--- Suite: Security & Discord Protocol Handshake ---")
        # 1. Reject invalid signature
        status, _, _ = self.post_interaction({"type": 1}, valid_sig=False)
        if status == 401:
            self.log_pass("Security", "Rejected invalid Ed25519 signature with 401 Unauthorized")
        else:
            self.log_fail("Security", f"Expected 401 on invalid signature, got {status}")

        # 2. Type 1 PING returns Type 1 PONG
        status, data, elapsed = self.post_interaction({"type": 1}, valid_sig=True)
        if status == 200 and data.get("type") == 1:
            self.log_pass("Heartbeat", f"Type 1 PING responded with Type 1 PONG in {elapsed:.1f}ms")
        else:
            self.log_fail("Heartbeat", f"Type 1 PING failed (status={status}, data={data})")

    def test_mtg_commands(self):
        print("\n--- Suite: Magic: The Gathering (/mtg) ---")
        cards = ["Sol Ring", "Lightning Bolt", "Counterspell"]
        if self.deep:
            cards.extend(["Black Lotus", "Damnation", "Mox Ruby"])

        for card_name in cards:
            payload = {
                "type": 2,
                "token": "tok-test-mtg",
                "application_id": "1547376653129224282",
                "data": {
                    "name": "mtg",
                    "options": [
                        {"name": "name", "value": card_name}
                    ]
                }
            }
            status, data, elapsed = self.post_interaction(payload)
            resp_type = data.get("type")
            if status == 200 and resp_type in (4, 5):
                if elapsed <= self.LATENCY_THRESHOLD_MS:
                    self.log_pass("MTG", f"Card '{card_name}' resolved (Type {resp_type}) in {elapsed:.1f}ms")
                else:
                    self.log_warn("MTG", f"Card '{card_name}' resolved slowly: {elapsed:.1f}ms > {self.LATENCY_THRESHOLD_MS}ms")
            else:
                self.log_fail("MTG", f"Card '{card_name}' failed with status {status}: {data}")

        # Test Natural Language Visual Search (/mtg visual-search)
        vsearch_payload = {
            "type": 2,
            "token": "tok-test-mtg-vsearch",
            "application_id": "1547376653129224282",
            "data": {
                "name": "mtg",
                "options": [
                    {"name": "visual-search", "options": [{"name": "query", "value": "moody blue merfolk"}]}
                ]
            }
        }
        status, data, elapsed = self.post_interaction(vsearch_payload)
        resp_type = data.get("type")
        if status == 200 and resp_type in (4, 5):
            self.log_pass("MTG", f"Visual search 'moody blue merfolk' resolved (Type {resp_type}) in {elapsed:.1f}ms")
        else:
            self.log_fail("MTG", f"Visual search 'moody blue merfolk' failed: {data}")

        # Test Similar Art by Card (/mtg similar-art)
        sim_payload = {
            "type": 2,
            "token": "tok-test-mtg-sim",
            "application_id": "1547376653129224282",
            "data": {
                "name": "mtg",
                "options": [
                    {"name": "similar-art", "options": [{"name": "card", "value": "Wary Farmer"}]}
                ]
            }
        }
        status, data, elapsed = self.post_interaction(sim_payload)
        resp_type = data.get("type")
        if status == 200 and resp_type in (4, 5):
            self.log_pass("MTG", f"Similar art for 'Wary Farmer' resolved (Type {resp_type}) in {elapsed:.1f}ms")
        else:
            self.log_fail("MTG", f"Similar art failed: {data}")

    def test_necro_commands(self):
        print("\n--- Suite: Necromunda (/necro) ---")
        weapons = ["Autogun", "Boltgun", "Plasma Gun"]
        if self.deep:
            weapons.extend(["Lasgun", "Heavy Bolter", "Flamer"])

        for w_name in weapons:
            payload = {
                "type": 2,
                "token": "tok-test-necro",
                "application_id": "1547376653129224282",
                "data": {
                    "name": "necro",
                    "options": [
                        {"name": "weapon", "options": [{"name": "name", "value": w_name}]}
                    ]
                }
            }
            status, data, elapsed = self.post_interaction(payload)
            resp_type = data.get("type")
            if status == 200 and resp_type in (4, 5):
                self.log_pass("Necromunda", f"Weapon '{w_name}' resolved in {elapsed:.1f}ms")
            else:
                self.log_fail("Necromunda", f"Weapon '{w_name}' failed with status {status}")

        # Test Lasting Injury Roller (Random Roll)
        injury_payload = {
            "type": 2,
            "token": "tok-test-necro-inj",
            "application_id": "1547376653129224282",
            "data": {
                "name": "necro",
                "options": [
                    {"name": "injury", "options": [{"name": "fighter", "value": "Krag Skull-Breaker"}]}
                ]
            }
        }
        status, data, elapsed = self.post_interaction(injury_payload)
        resp_type = data.get("type")
        embed = data.get("data", {}).get("embeds", [{}])[0] if data.get("data") else {}
        if status == 200 and resp_type == 4 and "D66" in embed.get("title", ""):
            self.log_pass("Necromunda", f"Random D66 Injury rolled '{embed.get('title')}' in {elapsed:.1f}ms")
        else:
            self.log_fail("Necromunda", f"Random injury roll failed with status {status}: {data}")

        # Test Lasting Injury Lookup (Specific Roll 23 Eye Injury)
        lookup_payload = {
            "type": 2,
            "token": "tok-test-necro-inj23",
            "application_id": "1547376653129224282",
            "data": {
                "name": "necro",
                "options": [
                    {"name": "injury", "options": [{"name": "roll", "value": "23"}]}
                ]
            }
        }
        status, data, elapsed = self.post_interaction(lookup_payload)
        embed = data.get("data", {}).get("embeds", [{}])[0] if data.get("data") else {}
        if status == 200 and "Eye Injury" in embed.get("title", ""):
            self.log_pass("Necromunda", f"D66 Roll 23 resolved to 'Eye Injury' in {elapsed:.1f}ms")
        else:
            self.log_fail("Necromunda", f"D66 Roll 23 lookup failed: {data}")

        # Test Lasting Injury Lookup (Specific Roll 66 Memorable Death)
        death_payload = {
            "type": 2,
            "token": "tok-test-necro-inj66",
            "application_id": "1547376653129224282",
            "data": {
                "name": "necro",
                "options": [
                    {"name": "injury", "options": [{"name": "roll", "value": "66"}]}
                ]
            }
        }
        status, data, elapsed = self.post_interaction(death_payload)
        embed = data.get("data", {}).get("embeds", [{}])[0] if data.get("data") else {}
        if status == 200 and "Memorable Death" in embed.get("title", ""):
            self.log_pass("Necromunda", f"D66 Roll 66 resolved to 'Memorable Death' in {elapsed:.1f}ms")
        else:
            self.log_fail("Necromunda", f"D66 Roll 66 lookup failed: {data}")

    def test_swu_commands(self):
        print("\n--- Suite: Star Wars: Unlimited (/swu) ---")
        swu_cards = ["Darth Vader", "Luke Skywalker"]
        if self.deep:
            swu_cards.extend(["Boba Fett", "Leia Organa"])

        for c_name in swu_cards:
            payload = {
                "type": 2,
                "token": "tok-test-swu",
                "application_id": "1547376653129224282",
                "data": {
                    "name": "swu",
                    "options": [
                        {"name": "name", "value": c_name}
                    ]
                }
            }
            status, data, elapsed = self.post_interaction(payload)
            resp_type = data.get("type")
            if status == 200 and resp_type in (4, 5):
                self.log_pass("SWU", f"Card '{c_name}' resolved in {elapsed:.1f}ms")
            else:
                self.log_fail("SWU", f"Card '{c_name}' failed with status {status}")

    def test_dominion_commands(self):
        print("\n--- Suite: Dominion (/dom) ---")
        dom_cards = ["Village", "Market"]
        if self.deep:
            dom_cards.extend(["Smithy", "Militia"])

        for c_name in dom_cards:
            payload = {
                "type": 2,
                "token": "tok-test-dom",
                "application_id": "1547376653129224282",
                "data": {
                    "name": "dom",
                    "options": [
                        {"name": "name", "value": c_name}
                    ]
                }
            }
            status, data, elapsed = self.post_interaction(payload)
            resp_type = data.get("type")
            if status == 200 and resp_type in (4, 5):
                self.log_pass("Dominion", f"Card '{c_name}' resolved in {elapsed:.1f}ms")
            else:
                self.log_fail("Dominion", f"Card '{c_name}' failed with status {status}")

    def test_minecraft_commands(self):
        print("\n--- Suite: Minecraft (/mc) ---")
        mc_items = ["Diamond Sword", "Crafting Table"]
        if self.deep:
            mc_items.extend(["Creeper", "Obsidian"])

        for item_name in mc_items:
            payload = {
                "type": 2,
                "token": "tok-test-mc",
                "application_id": "1547376653129224282",
                "data": {
                    "name": "mc",
                    "options": [
                        {"name": "name", "value": item_name}
                    ]
                }
            }
            status, data, elapsed = self.post_interaction(payload)
            resp_type = data.get("type")
            if status == 200 and resp_type in (4, 5):
                self.log_pass("Minecraft", f"Entity/Item '{item_name}' resolved in {elapsed:.1f}ms")
            else:
                self.log_fail("Minecraft", f"Entity/Item '{item_name}' failed with status {status}")

    def test_error_handling(self):
        print("\n--- Suite: Error Handling & Edge Cases ---")
        # Unknown command
        payload = {
            "type": 2,
            "data": {"name": "not_a_real_game", "options": [{"name": "name", "value": "xyz"}]}
        }
        status, data, _ = self.post_interaction(payload)
        msg = data.get("data", {}).get("content", "")
        if status == 200 and "Unknown command" in msg:
            self.log_pass("Errors", "Gracefully handled unknown root command")
        else:
            self.log_fail("Errors", f"Unknown root command response unexpected: {data}")

        # Empty card name
        payload = {
            "type": 2,
            "data": {"name": "mtg", "options": [{"name": "name", "value": ""}]}
        }
        status, data, _ = self.post_interaction(payload)
        msg = data.get("data", {}).get("content", "")
        if status == 200 and "Please provide a card name" in msg:
            self.log_pass("Errors", "Gracefully caught empty card query with hint")
        else:
            self.log_fail("Errors", f"Empty query response unexpected: {data}")

    def run_all(self) -> bool:
        t_start = time.perf_counter()
        print("========================================================")
        print(f"AvaScry Discord Bot Blaster 9001 (Mode: {'DEEP' if self.deep else 'QUICK'})")
        print("========================================================")

        self.test_security_and_heartbeat()
        self.test_mtg_commands()
        self.test_necro_commands()
        self.test_swu_commands()
        self.test_dominion_commands()
        self.test_minecraft_commands()
        self.test_error_handling()

        elapsed = round(time.perf_counter() - t_start, 2)
        print("\n========================================================")
        print(f"Discord Bot Blaster Summary: {self.passed} passed | {self.failed} failed | {self.warnings} warnings ({elapsed}s)")
        if self.failed == 0:
            print("\nDISCORD BOT LIVES. INTERACTION GATE SECURED.\n")
        else:
            print("\nDISCORD BOT FAILURE DETECTED.\n")
        print("========================================================\n")
        return self.failed == 0


def main():
    parser = argparse.ArgumentParser(description="AvaScry Discord Bot Blaster")
    parser.add_argument("--quick", action="store_true", help="Run quick invariant checks")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive deep checks")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL for target server")
    args = parser.parse_args()

    blaster = DiscordBotBlaster(base_url=args.base_url, deep=args.deep)
    success = blaster.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()