import json
from base64 import b64decode, b64encode
from typing import Optional
import itsdangerous
from starlette.requests import HTTPConnection
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

class NetworkSessionMiddleware:
    """
    Multi-domain aware session middleware for AvaScry Network.
    Automatically assigns Domain=.avascry.com when requests arrive on avascry.com or any subsite (*.avascry.com),
    enabling seamless Single Sign-On across MTG, SWU, Dominion, and Necromunda.
    Falls back gracefully on localhost/test environments without domain rejection.
    """
    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        session_cookie: str = "avascry_session",
        max_age: int = 14 * 24 * 3600,
        same_site: str = "lax",
        https_only: bool = False,
        domain: Optional[str] = None,
    ) -> None:
        self.app = app
        self.signer = itsdangerous.TimestampSigner(str(secret_key))
        self.session_cookie = session_cookie
        self.max_age = max_age
        self.same_site = same_site
        self.https_only = https_only
        self.configured_domain = domain

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True

        if self.session_cookie in connection.cookies:
            data = connection.cookies[self.session_cookie].encode("utf-8")
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope["session"] = json.loads(b64decode(data))
                initial_session_was_empty = False
            except Exception:
                scope["session"] = {}
        else:
            scope["session"] = {}

        # Resolve cookie domain dynamically based on incoming host
        host = connection.headers.get("x-forwarded-host") or connection.headers.get("host") or ""
        hostname = host.split(":")[0].lower()
        cookie_domain = self.configured_domain
        if not cookie_domain and (hostname == "avascry.com" or hostname.endswith(".avascry.com")):
            cookie_domain = ".avascry.com"

        security_flags = f"httponly; samesite={self.same_site}"
        if self.https_only:
            security_flags += "; secure"
        if cookie_domain:
            security_flags += f"; domain={cookie_domain}"

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                session = scope.get("session")
                headers = MutableHeaders(scope=message)
                if session:
                    data = b64encode(json.dumps(session).encode("utf-8"))
                    data = self.signer.sign(data)
                    header_value = "{session_cookie}={data}; path=/; {max_age}{security_flags}".format(
                        session_cookie=self.session_cookie,
                        data=data.decode("utf-8"),
                        max_age=f"Max-Age={self.max_age}; " if self.max_age else "",
                        security_flags=security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
                elif not initial_session_was_empty:
                    header_value = "{session_cookie}=null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; {security_flags}".format(
                        session_cookie=self.session_cookie,
                        security_flags=security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)
