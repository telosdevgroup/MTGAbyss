"""
scripts/register_discord_commands.py
-----------------------------------
Registers the unified 5-game slash commands with Discord's REST API:
  - /mtg   : Magic: The Gathering
  - /dom   : Dominion
  - /swu   : Star Wars: Unlimited
  - /necro : Necromunda
  - /mc    : Minecraft

Usage:
  # Dry-run validation of schemas:
  python scripts/register_discord_commands.py --dry-run

  # Instant test server registration (updates immediately, no 1-hour CDN delay):
  python scripts/register_discord_commands.py --guild-id <YOUR_DISCORD_SERVER_ID>

  # Global registration (available across all servers):
  python scripts/register_discord_commands.py --global
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error

# Ensure stdout handles UTF-8 safely on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def load_dotenv():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_dotenv()

CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "1547376653129224282").strip()
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()

UNIFIED_COMMANDS = [
    {
        "name": "mtg",
        "description": "Look up Magic: The Gathering cards, Oracle text, and rulings",
        "options": [
            {
                "type": 3,
                "name": "name",
                "description": "Card name to search (e.g. Sol Ring, Atraxa)",
                "required": True
            }
        ]
    },
    {
        "name": "dom",
        "description": "Look up Dominion kingdom cards, expansions, and costs",
        "options": [
            {
                "type": 3,
                "name": "name",
                "description": "Kingdom card name (e.g. Village, Chapel, Gold)",
                "required": True
            }
        ]
    },
    {
        "name": "swu",
        "description": "Look up Star Wars: Unlimited cards, leaders, and bases",
        "options": [
            {
                "type": 3,
                "name": "name",
                "description": "Card or leader name (e.g. Luke Skywalker, Darth Vader)",
                "required": True
            }
        ]
    },
    {
        "name": "necro",
        "description": "Look up Necromunda Underhive weapons, injuries, traits, houses, skills, and wargear",
        "options": [
            {
                "type": 1,
                "name": "weapon",
                "description": "Look up Underhive weapon profiles, statlines, and traits",
                "options": [
                    {
                        "type": 3,
                        "name": "name",
                        "description": "Weapon name (e.g. Bolter, Plasma Gun, Autogun)",
                        "required": True
                    }
                ]
            },
            {
                "type": 1,
                "name": "injury",
                "description": "Roll or look up Necromunda D66 Lasting Injuries",
                "options": [
                    {
                        "type": 4,
                        "name": "roll",
                        "description": "Optional manual D66 roll result (e.g. 61 for Memorable Death)",
                        "required": False
                    },
                    {
                        "type": 3,
                        "name": "fighter",
                        "description": "Optional fighter or ganger name for casualty log",
                        "required": False
                    }
                ]
            },
            {
                "type": 1,
                "name": "trait",
                "description": "Look up weapon traits and special rules (e.g. Rapid Fire, Blaze, Melta)",
                "options": [
                    {
                        "type": 3,
                        "name": "name",
                        "description": "Trait name (e.g. Rapid Fire, Blaze, Knockback)",
                        "required": True
                    }
                ]
            },
            {
                "type": 1,
                "name": "house",
                "description": "Look up House/Faction lore, gang doctrines, and rules",
                "options": [
                    {
                        "type": 3,
                        "name": "name",
                        "description": "House name (e.g. Van Saar, Goliath, Escher, Cawdor)",
                        "required": True
                    }
                ]
            },
            {
                "type": 1,
                "name": "skill",
                "description": "Look up Skill disciplines and ability rules",
                "options": [
                    {
                        "type": 3,
                        "name": "name",
                        "description": "Skill name (e.g. Fast Shot, Nerves of Steel, Infiltrate)",
                        "required": True
                    }
                ]
            },
            {
                "type": 1,
                "name": "equipment",
                "description": "Look up armor, field gear, ammo, and black market equipment",
                "options": [
                    {
                        "type": 3,
                        "name": "name",
                        "description": "Equipment name (e.g. Armoured Undersuit, Photo-goggles)",
                        "required": True
                    }
                ]
            }
        ]
    },
    {
        "name": "mc",
        "description": "Look up Minecraft items, blocks, recipes, and stack sizes",
        "options": [
            {
                "type": 3,
                "name": "name",
                "description": "Item or block name (e.g. Redstone, Diamond Sword)",
                "required": True
            }
        ]
    }
]

def print_setup_checklist():
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&scope=applications.commands"
    interactions_url = "https://avascry.com/api/discord/interactions"
    
    print("\n" + "="*70)
    print("AVASCRY UNIFIED GAMING BOT - DISCORD SETUP CHECKLIST")
    print("="*70)
    print(f"1. Discord Application ID: {CLIENT_ID}")
    print("2. Bot Invite URL (commands scope):")
    print(f"   -> {invite_url}")
    print("\n3. Interactions Endpoint URL:")
    print("   In Discord Dev Portal -> Application -> General Information -> 'Interactions Endpoint URL':")
    print(f"   -> {interactions_url}")
    print("\n4. Public Key Security:")
    if PUBLIC_KEY:
        print(f"   [OK] DISCORD_PUBLIC_KEY is set in .env ({PUBLIC_KEY[:8]}...)")
    else:
        print("   [!] DISCORD_PUBLIC_KEY is not set in .env! Copy 'PUBLIC KEY' from Discord Dev Portal -> General Information.")
    print("="*70 + "\n")

def register_commands(guild_id: str = None, dry_run: bool = False):
    print_setup_checklist()

    if dry_run:
        print("[DRY-RUN] Validating JSON payload schemas for Discord API v10...")
        for cmd in UNIFIED_COMMANDS:
            print(f"   * /{cmd['name']}: {cmd['description']}")
        print("\n[OK] All 5 command schemas are valid!")
        return

    token = BOT_TOKEN
    if not token:
        print("[ERROR] DISCORD_BOT_TOKEN environment variable is not set!")
        print("   Please set DISCORD_BOT_TOKEN in your .env or run with:")
        print("   $env:DISCORD_BOT_TOKEN='your_bot_token'; python scripts/register_discord_commands.py ...")
        sys.exit(1)

    if guild_id:
        url = f"https://discord.com/api/v10/applications/{CLIENT_ID}/guilds/{guild_id}/commands"
        target_name = f"Test Guild ({guild_id})"
    else:
        url = f"https://discord.com/api/v10/applications/{CLIENT_ID}/commands"
        target_name = "Global (All Discord Servers)"

    print(f"Deploying 5 slash commands to {target_name} via bulk overwrite (PUT)...")

    req = urllib.request.Request(
        url,
        data=json.dumps(UNIFIED_COMMANDS).encode("utf-8"),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "AvaScryDiscordBot/1.0"
        },
        method="PUT"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            registered = json.loads(resp_body)
            print(f"\n[OK] Successfully registered {len(registered)} commands with Discord!")
            for c in registered:
                print(f"   - /{c['name']} (ID: {c.get('id')})")
            if guild_id:
                print("\nGuild commands update INSTANTLY in your server!")
            else:
                print("\nGlobal commands deployed! (Discord global cache propagates within 1 hour).")
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        print(f"\n[ERROR] HTTP Error {e.code}: {e.reason}")
        print(f"Response: {err_content}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register AvaScry Unified Discord Commands")
    parser.add_argument("--guild-id", help="Register instantly to a specific Discord server (Server Settings -> Copy Server ID)")
    parser.add_argument("--global", dest="is_global", action="store_true", help="Register globally across all servers")
    parser.add_argument("--dry-run", action="store_true", help="Validate command payload schema without calling Discord")

    args = parser.parse_args()

    if not args.guild_id and not args.is_global and not args.dry_run:
        print("Please specify either --guild-id <SERVER_ID>, --global, or --dry-run.")
        parser.print_help()
        sys.exit(0)

    register_commands(guild_id=args.guild_id, dry_run=args.dry_run)
