import os
import socket
from dotenv import load_dotenv

load_dotenv()

# Silence Windows asyncio proactor WinError 10054 on sudden client disconnects
if os.name == 'nt':
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _orig_call_conn_lost = _ProactorBasePipeTransport._call_connection_lost

        def _silent_conn_lost(self, exc=None):
            try:
                if getattr(self, '_sock', None) is not None:
                    self._sock.shutdown(socket.SHUT_RDWR)
            except (ConnectionResetError, OSError):
                pass
            try:
                _orig_call_conn_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass
        _ProactorBasePipeTransport._call_connection_lost = _silent_conn_lost
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from mtgabyss.network_router import extract_subdomain, get_request_host
from mtgabyss.middleware.bot_shield import register_bot_shield
from mtgabyss.middleware.access_logger import register_access_logger
from mtgabyss.shared.helpers import (
    slugify, is_commander_eligible, render_template, find_card_by_slug,
    build_card_view_model, resolve_card_images, get_scryfall_direct_uris,
    templates, safe_header_segment
)
from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache

# Existing Subsite Routers
from mtgabyss.dominion_router import dominion_router
from mtgabyss.swu_router import swu_router

# Extracted MTG Routers
from mtgabyss.routers.static_router import static_router
from mtgabyss.routers.image_router import image_router
from mtgabyss.routers.pages_router import pages_router
from mtgabyss.routers.auth_router import auth_router
from mtgabyss.routers.user_router import user_router
from mtgabyss.routers.commander_router import commander_router
from mtgabyss.routers.sets_router import sets_router
from mtgabyss.routers.artist_router import artist_router
from mtgabyss.routers.card_router import card_router
from mtgabyss.routers.api_router import api_router

app = FastAPI(title="AvaScry", description="Magic: The Gathering Visual Explorer & Strategy Engine")

SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "fallback-insecure-secret-key-32-bytes-min")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="avascry_session",
    max_age=14 * 24 * 3600,  # 14 days
    same_site="lax",
    https_only=False  # Allow http for local development; cookies still work behind https proxy
)

# Ensure static & image directories exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("public/images/normal", exist_ok=True)
os.makedirs("public/images/large", exist_ok=True)
os.makedirs("public/images/swu", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="public/images"), name="images")

# Subsite Routers
app.include_router(dominion_router, prefix="/dominion")
app.include_router(swu_router, prefix="/swu")

# Extracted MTG Routers
app.include_router(static_router)
app.include_router(image_router)
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(commander_router)
app.include_router(sets_router)
app.include_router(artist_router)
app.include_router(card_router)
app.include_router(api_router)


# Middlewares (Registered in order: Request logging -> Localization -> Bot Shield -> Subdomain)
# Note: FastAPI evaluates HTTP middlewares in reverse registration order.
register_access_logger(app)  # executes request_logger & add_localization_context
register_bot_shield(app)     # executes bot_probe_shield_middleware


@app.middleware("http")
async def subdomain_routing_middleware(request: Request, call_next):
    """
    Subdomain Host Routing:
    If host is dominion.avascry.com or dominion.localhost, rewrite the internal path
    to route directly into the dominion router.
    If host is swu.avascry.com or starwars.avascry.com, rewrite to /swu router.
    """
    host = get_request_host(request)
    sub = extract_subdomain(host)
    if sub == "dominion":
        path = request.scope.get("path", "")
        if not path.startswith("/dominion") and not path.startswith("/static") and not path.startswith("/images"):
            request.scope["path"] = "/dominion" + path
    elif sub == "swu":
        path = request.scope.get("path", "")
        if not path.startswith("/swu") and not path.startswith("/static") and not path.startswith("/images"):
            request.scope["path"] = "/swu" + path
    return await call_next(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8004,
        reload=True,
        access_log=False
    )
