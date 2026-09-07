"""
Shared contact handler for the AvaScry network.
Standardizes contact form submissions, anti-spam honeypots, character limits,
and Discord webhook dispatching across all game subsites.
"""

from typing import Dict, Any, Optional
from fastapi import Request
import mtgabyss.routers.auth_router as auth_module

MAX_MESSAGE_LENGTH = 500
MAX_NAME_LENGTH = 80
MAX_CONTACT_LENGTH = 100



async def process_contact_submission(
    request: Request,
    subsite_name: str,
    subsite_color: int = 0x5865F2,
    extra_field_name: Optional[str] = None,
    extra_field_label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates form data and dispatches to Discord webhook if valid.
    Returns a dict with 'success' (bool), 'error' (Optional[str]), and 'values' (dict of submitted fields).
    """
    form = await request.form()

    # 1. Anti-spam honeypot
    honeypot = str(form.get("website_url", "")).strip()
    if honeypot:
        # Silently pretend success to deceive spam bots without webhook traffic
        return {"success": True, "error": None, "values": {}}

    name = str(form.get("name", "")).strip()[:MAX_NAME_LENGTH]
    contact_info = str(form.get("contact", "")).strip()[:MAX_CONTACT_LENGTH]
    message = str(form.get("message", "")).strip()

    extra_val = ""
    if extra_field_name:
        extra_val = str(form.get(extra_field_name, "")).strip()

    if not name or not contact_info or not message:
        return {
            "success": False,
            "error": "Please fill out all required fields before submitting.",
            "values": {
                "name": name,
                "contact": contact_info,
                "message": message,
                "extra": extra_val
            }
        }

    # Truncate message to standardized length limit
    clipped_message = message[:MAX_MESSAGE_LENGTH]

    # 2. Build Discord embed
    fields = [
        {"name": "Subsite", "value": subsite_name, "inline": True},
        {"name": "Sender", "value": name, "inline": True},
        {"name": "Contact", "value": contact_info, "inline": True},
    ]

    if extra_val and extra_field_label:
        fields.append({"name": extra_field_label, "value": extra_val[:100], "inline": True})

    fields.append({"name": "Message", "value": clipped_message, "inline": False})

    title = f"📩 [{subsite_name}] Message from {name}"
    description = f"New inquiry received on **{subsite_name}** from **{name}**."

    try:
        await auth_module.send_discord_notification(
            title=title,
            description=description,
            color=subsite_color,
            fields=fields
        )
    except Exception as exc:
        print(f"[{subsite_name} Contact] Failed to dispatch Discord notification: {exc}")

    return {"success": True, "error": None, "values": {}}
