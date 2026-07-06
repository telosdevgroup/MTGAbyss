import json
import hashlib

DEFAULT_SCHEMA = {
    "text": "string"
}

BANNED_PHRASES = [
    "notable card", "notable Artifact", "strategic value", "mechanical depth",
    "alters the game's flow", "demands respect", "speaks volumes", "unique mechanics",
    "iconic", "legendary card", "powerful artifact", "game-changing",
    "math", "game economy", "resource generation", "card design",
    "opening turn", "permanent scar", "turns nothing into three mana"
]

def get_prompt_hash(prompt_text):
    return hashlib.md5(prompt_text.encode('utf-8')).hexdigest()

def build_prompt(card_facts, language="en", section_type="hook", persona="default", output_schema=None):
    if section_type == "vignette_experiment":
        return """Write a 3-4 sentence unofficial fantasy vignette inspired by Black Lotus.

Perspective:
First person, from a mage who found the flower.

Style:
Quiet, human, mystical, restrained.
No epic fantasy clichés.
No “eternity,” “fabric of reality,” “older than time,” “storm,” “destiny,” or “power beyond imagination.”

Card inspiration:
The flower costs nothing to take, but must be destroyed to release its gift.
Its sacrifice gives the mage a sudden rush of three colors/streams of magical force.

The flower should feel rare, tempting, and dangerous.
The mage should feel awe mixed with fear.

Do not:
- Mention Magic: The Gathering.
- Mention rules terms.
- Mention mana cost.
- Mention Power Nine.
- Mention Vintage.
- Sound like a card review.
- Sound like SEO.
- Invent official canon.

Output:
Plain text only.
No JSON unless the current worker absolutely requires JSON. If JSON is required, use only:
{
  "text": "..."
}

Output only the vignette."""

    if output_schema is None:
        output_schema = DEFAULT_SCHEMA
        
    schema_str = json.dumps(output_schema, indent=2)

    # Gather precise card stats
    name = card_facts.get("name", "Unknown Card")
    type_line = card_facts.get("type_line", "") or ""
    oracle_text = card_facts.get("oracle_text", "") or ""
    mana_cost = card_facts.get("mana_cost") or "None"
    cmc = card_facts.get("cmc") or 0.0
    color_identity = card_facts.get("color_identity", [])
    keywords = card_facts.get("keywords", [])
    legalities = card_facts.get("legalities", {})
    reserved = card_facts.get("reserved", False)

    # Check if certain details exist in the card source facts
    is_restricted = legalities.get("vintage") == "restricted"
    is_power_nine = name.lower() == "black lotus"

    source_details = []
    if is_restricted:
        source_details.append("- Legality details confirm it is restricted in the Vintage format.")
    if is_power_nine:
        source_details.append("- It is historically grouped within the legendary 'Power Nine'.")

    source_details_str = "\n".join(source_details)

    banned_clause = ", ".join([f'"{phrase}"' for phrase in BANNED_PHRASES])

    prompt = f"""You are an AI archivist writing a single-sentence hook/intrigue line for MTGAbyss, a site dedicated to strange, dark commentary and static archives of Magic: The Gathering cards.

Card Facts (Strict Truth):
- Name: {name}
- Type Line: {type_line}
- Oracle Text: {oracle_text}
- Mana Cost: {mana_cost} (Mana Value: {cmc})
- Color Identity: {", ".join(color_identity) if color_identity else "Colorless"}
- Keywords: {", ".join(keywords) if keywords else "None"}
- Reserved List: {"Yes (Reserved List card)" if reserved else "No"}
{source_details_str}

Objective:
Write exactly ONE sentence (a short hook, intrigue line, or summary) about this card. The tone must feel:
- mystical
- human
- strange
- old-world
- quietly powerful
- poetic but not cheesy
- like someone whispering about a forbidden relic

Prose Requirements:
- Word Count: Exactly between 10 and 24 words.
- Specificity: It must be highly specific to {name}.
- Concrete Facts: You may gently imply its zero mana cost, its sacrifice, its creation of three mana, its status in the Power Nine, or its restricted nature. However, it should NOT sound like a rules explanation, a database summary, database/strategy language, or finance/SEO language.
- Style:
  - Do NOT invent physical, artwork, or lore details.
  - Make it feel quietly powerful.

CRITICAL RULES:
1. DO NOT use any of the following banned phrases or terms: [{banned_clause}].
2. Output MUST be a raw JSON object matching this schema. No markdown formatting blocks around it:
{schema_str}
"""
    return prompt
