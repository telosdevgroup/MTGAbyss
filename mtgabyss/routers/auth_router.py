import os
import secrets
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from db_mongo import get_mongo_db
import i18n
from mtgabyss.shared.helpers import templates
from mtgabyss.network_router import extract_subdomain, get_request_host

auth_router = APIRouter()

def is_safe_redirect(url: Optional[str]) -> bool:
    """Validate that redirect target is strictly a safe local path or a trusted AvaScry subdomain."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if "\\" in url:
        return False
    # Relative path
    if url.startswith("/") and not url.startswith("//"):
        if url.startswith("/auth"):
            return False
        return True
    # Fully-qualified URL to trusted AvaScry network or local dev
    if "://" in url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            netloc = parsed.netloc.lower().split(":")[0]
            if netloc == "avascry.com" or netloc.endswith(".avascry.com") or netloc == "localhost" or netloc.endswith(".localhost"):
                if parsed.path.startswith("/auth"):
                    return False
                return True
        except Exception:
            return False
    return False

def resolve_redirect_url(request: Request, next_url: Optional[str], fallback_path: str = "/dashboard") -> str:
    """Resolve redirect target, ensuring relative paths on subsites retain the subsite origin."""
    host = get_request_host(request)
    sub = extract_subdomain(host)
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)

    if next_url and is_safe_redirect(next_url):
        if next_url.startswith("/") and sub:
            return f"{proto}://{host}{next_url}"
        return next_url

    if sub:
        return f"{proto}://{host}/"
    return fallback_path

def get_base_url(request: Request) -> str:
    """Resolve correct base URL honoring Cloudflare / reverse proxy headers."""
    env_base = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    if env_base:
        return env_base
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    host_parts = host.split(":")
    hostname = host_parts[0].lower()
    port_str = f":{host_parts[1]}" if len(host_parts) > 1 else ""

    if hostname == "avascry.com" or hostname.endswith(".avascry.com"):
        return f"{proto}://avascry.com"
    if hostname.endswith(".localhost"):
        return f"{proto}://localhost{port_str}"
    return f"{proto}://{host}"

async def send_discord_notification(title: str, description: str, color: int = 0x5865F2, fields: Optional[List[Dict[str, Any]]] = None, image_url: Optional[str] = None):
    """Fire-and-forget Discord webhook notification with rich embed."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return
    
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if fields:
        embed["fields"] = fields
    if image_url:
        embed["image"] = {"url": image_url}

    payload = {
        "username": "AvaScry Bot",
        "embeds": [embed]
    }
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(webhook_url, json=payload)
    except Exception as exc:
        print(f"[Discord Webhook] Failed to send notification: {exc}")

@auth_router.get("/auth/login", response_class=HTMLResponse)
async def auth_login_choice(request: Request, next: Optional[str] = None):
    redirect_target = resolve_redirect_url(request, next, fallback_path="/dashboard")
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "active_nav": "login",
            "current_lang": lang,
            "next_url": redirect_target,
            "auth_error": request.query_params.get("auth_error"),
            "user": request.session.get("user")
        }
    )

@auth_router.get("/auth/discord/login")
async def auth_discord_login(request: Request, next: Optional[str] = None, popup: Optional[str] = None):
    client_id = os.environ.get("DISCORD_CLIENT_ID", "").strip()
    if not client_id:
        return HTMLResponse("<h3>Error: DISCORD_CLIENT_ID is not configured in .env</h3>", status_code=500)
    
    if popup == "1":
        request.session["is_popup"] = True
    else:
        request.session.pop("is_popup", None)
    
    return_target = next or request.headers.get("referer")
    redirect_target = resolve_redirect_url(request, return_target, fallback_path="/dashboard")
    redirect_uri = f"{get_base_url(request)}/auth/discord/callback"
    request.session["oauth_next"] = redirect_target
    
    # If already logged in, store linking user ID
    curr_user = request.session.get("user")
    if curr_user and curr_user.get("id"):
        request.session["linking_user_id"] = curr_user["id"]
    
    oauth_state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = oauth_state
    
    auth_url = (
        "https://discord.com/oauth2/authorize?"
        + httpx.QueryParams({
            "client_id": client_id,
            "response_type": "code",
            "scope": "identify email",
            "redirect_uri": redirect_uri,
            "state": oauth_state,
        }).__str__()
    )
    return RedirectResponse(url=auth_url, status_code=303)

@auth_router.get("/auth/discord/callback")
async def auth_discord_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    is_popup = request.session.get("is_popup", False)
    if error or not code:
        print(f"[Discord Callback] Error received: {error}")
        if request.session.pop("is_popup", False):
            return HTMLResponse("<script>window.close();</script>", status_code=200)
        return RedirectResponse(url=f"/auth/login?auth_error={error or 'cancelled'}", status_code=303)
    
    saved_state = request.session.pop("oauth_state", None)
    if not saved_state or not state or not secrets.compare_digest(saved_state, state):
        print("[Discord Callback] State mismatch detected")
        if request.session.pop("is_popup", False):
            return HTMLResponse("<script>window.close();</script>", status_code=200)
        return RedirectResponse(url="/auth/login?auth_error=invalid_oauth_state", status_code=303)
    
    client_id = os.environ.get("DISCORD_CLIENT_ID", "").strip()
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET", "").strip()
    redirect_uri = f"{get_base_url(request)}/auth/discord/callback"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://discord.com/api/v10/oauth2/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if token_resp.status_code != 200:
                print(f"[Discord Callback] Token exchange failed: {token_resp.text}")
                return RedirectResponse(url="/auth/login?auth_error=token_exchange_failed", status_code=303)
                
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            
            user_resp = await client.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_resp.status_code != 200:
                print(f"[Discord Callback] User info fetch failed: {user_resp.text}")
                return RedirectResponse(url="/auth/login?auth_error=userinfo_failed", status_code=303)
                
            discord_user = user_resp.json()
            
        discord_id = discord_user.get("id")
        discord_username = discord_user.get("username", "Planeswalker")
        email = discord_user.get("email", "")
        avatar_hash = discord_user.get("avatar")
        picture = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png" if avatar_hash else ""
        
        db = get_mongo_db()
        now = datetime.now(timezone.utc).isoformat()
        
        # Dual-identity merge / link
        linking_user_id = request.session.pop("linking_user_id", None)
        existing_user = None
        if linking_user_id:
            try:
                from bson import ObjectId
                existing_user = db["users"].find_one({"_id": ObjectId(linking_user_id)})
            except Exception:
                pass
                
        if not existing_user:
            query = {"discord_id": discord_id}
            if email:
                query = {"$or": [{"discord_id": discord_id}, {"email": email}]}
            existing_user = db["users"].find_one(query)
            
        if existing_user:
            update_data = {
                "discord_id": discord_id,
                "discord_username": discord_username,
                "updated_at": now
            }
            if picture and not existing_user.get("picture"):
                update_data["picture"] = picture
            if not existing_user.get("name") or existing_user.get("name") == "Magic Player":
                update_data["name"] = discord_username
            if email and not existing_user.get("email"):
                update_data["email"] = email
                
            db["users"].update_one({"_id": existing_user["_id"]}, {"$set": update_data})
            user_doc = db["users"].find_one({"_id": existing_user["_id"]})
        else:
            new_doc = {
                "discord_id": discord_id,
                "discord_username": discord_username,
                "name": discord_username,
                "email": email,
                "picture": picture,
                "created_at": now,
                "updated_at": now
            }
            res = db["users"].insert_one(new_doc)
            user_doc = db["users"].find_one({"_id": res.inserted_id})
            asyncio.create_task(send_discord_notification(
                title="✨ New User Signup (Discord)",
                description=f"**{discord_username}** joined AvaScry via Discord OAuth!",
                color=0x5865F2,
                fields=[
                    {"name": "Username", "value": discord_username, "inline": True},
                    {"name": "Account ID", "value": str(res.inserted_id), "inline": True}
                ]
            ))
            
        request.session["user"] = {
            "id": str(user_doc["_id"]),
            "discord_id": discord_id,
            "discord_username": discord_username,
            "google_sub": user_doc.get("google_sub"),
            "name": user_doc.get("name", discord_username),
            "email": user_doc.get("email", ""),
            "picture": user_doc.get("picture", "")
        }
        
        is_popup = request.session.pop("is_popup", False)
        raw_next = request.session.pop("oauth_next", None)
        next_url = raw_next if is_safe_redirect(raw_next) else "/dashboard"
        
        if is_popup:
            popup_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Authentication Complete</title></head>
<body style="background:#090a0f;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;font-family:system-ui,-apple-system,sans-serif;">
<div style="text-align:center;">
  <p style="font-weight:700;font-size:1.1rem;margin:0 0 0.5rem;">Signed in with Discord</p>
  <p style="font-size:0.85rem;color:#a1a1aa;margin:0;">Returning to application...</p>
</div>
<script>
  try {{
    if (window.opener && !window.opener.closed) {{
      window.opener.location.reload();
      window.close();
    }} else {{
      window.location.href = "{next_url}";
    }}
  }} catch (e) {{
    window.location.href = "{next_url}";
  }}
</script>
</body>
</html>"""
            return HTMLResponse(content=popup_html, status_code=200)

        return RedirectResponse(url=next_url, status_code=303)
    except Exception as e:
        print(f"[Discord Callback] Exception: {e}")
        if request.session.pop("is_popup", False):
            return HTMLResponse("<script>window.close();</script>", status_code=200)
        return RedirectResponse(url="/auth/login?auth_error=oauth_failed", status_code=303)

@auth_router.get("/auth/logout")
async def auth_logout(request: Request, next: Optional[str] = None):
    request.session.clear()
    target = resolve_redirect_url(request, next, fallback_path="/commander")
    return RedirectResponse(url=target, status_code=303)
