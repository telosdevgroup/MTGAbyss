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
        
    prompt = f"""Write one Abyss Lure for this Magic card. The Lure must be a single fully-developed, atmospheric paragraph (1–2 long, descriptive sentences) that invites a click rather than explaining the rules. It will also be used as the meta description. Make it concrete, strange, and card-specific. Output only the Lure.

Shape:
- Target length: 220–260 characters. Do NOT write a short, simple one-liner. Let the text develop into a rich, evocative paragraph.
- Soft max: 300 characters.
- Hard reject: 340+ characters.
- 1–2 sentences max.
- No line breaks.
- No markdown.
- No quotes wrapped around the whole output.
- No explanations.
- No “as an AI”.
- Do not summarize the card’s rules text.
- Do not say “this card”.
- Do not write strategy advice.
- Do not mention formats, decks, commanders, prices, legality, or gameplay tips.
- Do not output JSON.
- Do not output multiple candidates.

Style:
- Atmospheric, concrete, strange, and card-specific.
- It should feel like a small door into the card, or a fragment of an omen/myth that makes the reader curious enough to see where it leads.
- Prefer physical imagery, object imagery, creature behavior, omen, texture, motion, cost, hunger, oath, bloom, ash, glass, roots, metal, blood, wings, stone, etc. when appropriate.
- Avoid overusing vague fantasy filler like “void,” “shadow,” “whispers,” “ancient,” “forgotten,” “primordial,” unless it genuinely fits the card.

Source facts:
{facts_str}
"""
    return prompt, facts

def validate_lure_text(text, card_name):
    if not text or not text.strip():
        return False, "Lure text is empty."
    
    if "\n" in text or "\r" in text:
        return False, "Lure contains line breaks."
        
    text_len = len(text)
    if text_len >= 340:
        return False, f"Lure is too long ({text_len} characters, hard reject limit is 340)."
    if text_len < 80 or text_len > 320:
        return False, f"Lure length ({text_len} characters) is outside the accepted 80–320 range."
        
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return False, "Lure is entirely wrapped in quotes."
        
    lower_text = text.lower()
    
    if lower_text.startswith("lure:") or lower_text.startswith("meta description:"):
        return False, "Lure starts with an unwanted label."
        
    if "as an ai" in text.lower():
        return False, "Lure contains 'as an AI' preamble."
        
    if "{" in text or "}" in text or "```" in text:
        return False, "Lure contains code/JSON structures."
        
    if any(char in text for char in ["*", "#", "[", "]", "_", "`"]):
        return False, "Lure contains markdown styling."
        
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) < 1 or len(sentences) > 2:
        return False, f"Lure must be 1–2 sentences (found {len(sentences)})."
        
    lower_name = card_name.lower()
    clunky_patterns = [
        f"{lower_name} is a",
        f"{lower_name} is the",
        f"{lower_name} is one of",
        f"{lower_name} is legendary",
        f"this is the lure for {lower_name}",
        "as a magic commander",
        "magic card",
        "commander card",
        "this card",
        "commander deck",
        "edhrec",
        "deckbuilding",
        "strategic value",
        "synergy",
        "combo with",
        "rules text"
    ]
    for pattern in clunky_patterns:
        if pattern in lower_text:
            return False, f"Lure contains clunky card reference or strategy pattern: '{pattern}'"
            
    return True, ""
