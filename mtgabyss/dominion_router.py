"""
Dominion Sub-Application Router for dominion.avascry.com.
Connects directly to MongoDB database 'avascry_dominion'.
Serves HTML, Markdown (.md), JSON, and llms.txt endpoints for bots and humans.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from db_mongo import get_mongo_db

dominion_router = APIRouter(prefix="", tags=["Dominion"])

def get_dominion_db():
    client = get_mongo_db().client
    return client["avascry_dominion"]

@dominion_router.get("/llms.txt", response_class=PlainTextResponse)
async def dominion_llms_txt(request: Request):
    """Navigational manifest for LLM search agents."""
    return (
        "# AvaScry Dominion\n\n"
        "> Structured Dominion card, expansion, edition, and official rules data.\n\n"
        "## Start here\n"
        "- [All Cards](https://dominion.avascry.com/cards)\n"
        "- [Expansions](https://dominion.avascry.com/expansions)\n\n"
        "## Endpoints\n"
        "- Markdown: https://dominion.avascry.com/card/{slug}.md\n"
        "- JSON: https://dominion.avascry.com/card/{slug}.json\n"
        "- Full Corpus: https://dominion.avascry.com/llms-full.txt\n"
    )

@dominion_router.get("/card/{slug}.json")
async def dominion_card_json(slug: str):
    db = get_dominion_db()
    card = db.cards.find_one({"slug": slug}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    versions = list(db.card_versions.find({"card_id": f"card:{slug}"}, {"_id": 0}))
    rulings = list(db.rulings.find({"card_id": f"card:{slug}"}, {"_id": 0}))
    
    return {
        "card": card,
        "versions": versions,
        "rulings": rulings
    }

@dominion_router.get("/card/{slug}.md", response_class=PlainTextResponse)
async def dominion_card_markdown(slug: str):
    db = get_dominion_db()
    card = db.cards.find_one({"slug": slug})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    versions = list(db.card_versions.find({"card_id": f"card:{slug}"}))
    rulings = list(db.rulings.find({"card_id": f"card:{slug}"}))
    
    md = [
        f"# {card['name']}",
        f"**Types**: {', '.join(card.get('card_kinds', []))}",
        f"**Kingdom Card**: {'Yes' if card.get('is_kingdom_card') else 'No'}\n"
    ]
    
    if versions:
        md.append("## Versions & Costs")
        for v in versions:
            cost = v.get("cost", {})
            cost_str = f"{cost.get('coins', 0)} Coins"
            if cost.get("debt"):
                cost_str += f", {cost['debt']} Debt"
            if cost.get("potion"):
                cost_str += ", 1 Potion"
            md.append(f"### {v.get('expansion_tag', 'Base')} ({v.get('edition', 'standard')})")
            md.append(f"- **Cost**: {cost_str}")
            md.append(f"- **Text**: {v.get('printed_rules_text', '')}\n")
            
    if rulings:
        md.append("## Official Rulings & Rules FAQ")
        for r in rulings:
            md.append(f"**{r.get('question', '')}**\n")
            md.append(f"{r.get('answer', '')}\n")
            
    return "\n".join(md)
