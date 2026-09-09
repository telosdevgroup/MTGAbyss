"""
scripts/register_discord_commands.py — Registers AvaScry Slash Commands with Discord.

Usage:
    python scripts/register_discord_commands.py --bot-token YOUR_DISCORD_BOT_TOKEN
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error

COMMANDS = [
    {
        "name": "necro",
        "description": "Necromunda Underhive Armory, weapons & fighter rules",
        "options": [
            {
                "name": "weapon",
                "description": "Look up a weapon's ballistics profile and special rules",
                "type": 1,  # Subcommand
                "options": [
                    {
                        "name": "name",
                        "description": "Weapon name (e.g. bolter, stub gun, flamer)",
                        "type": 3,  # STRING
                        "required": True
                    }
                ]
            }
        ]
    },
    {
        "name": "swu",
        "description": "Star Wars: Unlimited card database & official rulings",
        "options": [
            {
                "name": "card",
                "description": "Look up a card's stats, aspects, abilities and rulings",
                "type": 1,  # Subcommand
                "options": [
                    {
                        "name": "name",
                        "description": "Card title (e.g. Luke Skywalker, Vader, Falcon)",
                        "type": 3,  # STRING
                        "required": True
                    }
                ]
            }
        ]
    },
    {
        "name": "mc",
        "description": "Minecraft comprehensive item & recipe directory",
        "options": [
            {
                "name": "item",
                "description": "Look up a Minecraft item's stack size and crafting info",
                "type": 1,  # Subcommand
                "options": [
                    {
                        "name": "name",
                        "description": "Item name (e.g. diamond pickaxe, redstone)",
                        "type": 3,  # STRING
                        "required": True
                    }
                ]
            }
        ]
    }
]

def main():
    parser = argparse.ArgumentParser(description="Register global Discord slash commands")
    parser.add_argument("--bot-token", help="Discord Bot Token")
    parser.add_argument("--client-id", default=os.environ.get("DISCORD_CLIENT_ID", "1543690979251462235"))
    args = parser.parse_args()

    token = args.bot_token or os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("[!] Missing Discord Bot Token. Pass via --bot-token or set DISCORD_BOT_TOKEN environment variable.")
        print("[*] You can find your Bot Token in the Discord Developer Portal -> Bot -> Reset Token.")
        sys.exit(1)

    url = f"https://discord.com/api/v10/applications/{args.client_id}/commands"
    req = urllib.request.Request(
        url,
        data=json.dumps(COMMANDS).encode("utf-8"),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json"
        },
        method="PUT"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[+] Successfully registered {len(data)} global Discord slash commands:")
            for cmd in data:
                print(f"    - /{cmd['name']}: {cmd['description']}")
    except urllib.error.HTTPError as e:
        print(f"[!] Discord API error: {e.code} - {e.read().decode('utf-8')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
