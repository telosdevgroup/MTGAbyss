import re

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def clean_lure_text(text):
    if not text:
        return ""
    text = text.strip()
    
    # Remove outer quotes if the model wrapped the entire answer in quotes
    while (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
        
    # Reject obvious preambles
    preambles = [
        "here is the lure:",
        "here is a lure:",
        "here is the mtgabyss lure:",
        "here is the lure for this magic commander:",
        "here is the lure text:",
        "here is the generated lure:"
    ]
    text_lower = text.lower()
    for preamble in preambles:
        if text_lower.startswith(preamble):
            text = text[len(preamble):].strip()
            # Also clean again for quotes if they were inside the preamble
            while (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1].strip()
            break
    return text

def build_lure_prompt(card):
    # Build a source facts packet from the card
    facts = {
        "name": card.get("name"),
        "type_line": card.get("type_line"),
        "oracle_text": card.get("oracle_text"),
        "keywords": card.get("keywords", []),
        "color_identity": card.get("color_identity", []),
        "power": card.get("power") or card.get("raw", {}).get("power"),
        "toughness": card.get("toughness") or card.get("raw", {}).get("toughness")
    }
    
    # Format facts as a nice text block
    facts_str = f"Name: {facts['name']}\n"
    facts_str += f"Type: {facts['type_line']}\n"
    if facts['oracle_text']:
        facts_str += f"Oracle Text:\n{facts['oracle_text']}\n"
    if facts['keywords']:
        facts_str += f"Keywords: {', '.join(facts['keywords'])}\n"
    if facts['color_identity']:
        facts_str += f"Color Identity: {', '.join(facts['color_identity'])}\n"
    if facts['power'] is not None and facts['toughness'] is not None:
        facts_str += f"Power/Toughness: {facts['power']}/{facts['toughness']}\n"
        
    prompt = f"""Write an MTGAbyss Lure for this Magic commander.

CRITICAL REQUIREMENT: You must write EXACTLY two (2) sentences. Do not write three sentences. Do not write a single sentence. The total length must be between 15 and 50 words.

The Lure is the first short AI-written text on a visual commander archive page. It should pull the reader into the commander’s Abyss.

Use the source facts, but do not mechanically list them.

Tone:
mystical, human, strange, elegant, ominous, intimate.

Voice:
Write like a quiet myth, a witness account, or a strange archive entry.

Do not:
- mention Magic: The Gathering
- mention EDHREC
- mention Commander format
- mention deckbuilding
- mention popularity
- mention rankings
- sound like a card review
- sound like a rules explanation
- claim this is official lore
- mechanically list abilities
- use phrases like “powerful commander,” “strategic value,” “game-changing,” “iconic,” or “synergy”

You may imply mechanics through imagery.
You may use exact mechanic words only if they feel natural.
Output only the Lure text.

Source facts:
{facts_str}
"""
    return prompt, facts

def validate_lure_text(text, card_name):
    if not text or not text.strip():
        return False, "Lure text is empty."
    
    words = text.split()
    if len(words) > 75:
        return False, f"Lure is too long ({len(words)} words, max 75)."
    if len(words) < 15:
        return False, f"Lure is too short ({len(words)} words, min 15)."
        
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) != 2:
        return False, f"Lure must be exactly 2 sentences (found {len(sentences)})."
        
    if any(char in text for char in ["*", "#", "[", "]", "_", "`"]):
        return False, "Lure contains markdown styling."
        
    if "as an ai" in text.lower():
        return False, "Lure contains 'as an AI' preamble."
        
    if "{" in text or "}" in text or "```" in text:
        return False, "Lure contains code/JSON structures."
        
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return False, "Lure is entirely wrapped in quotes."
        
    lower_text = text.lower()
    lower_name = card_name.lower()
    
    clunky_patterns = [
        f"{lower_name} is a",
        f"{lower_name} is the",
        f"{lower_name} is one of",
        f"{lower_name} is legendary",
        f"this is the lure for {lower_name}",
        "as a magic commander",
        "magic card",
        "commander card"
    ]
    for pattern in clunky_patterns:
        if pattern in lower_text:
            return False, f"Lure contains clunky card reference pattern: '{pattern}'"
            
    return True, ""
