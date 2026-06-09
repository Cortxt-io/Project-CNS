"""ASGI entrypoint – serves the remote MCP server and the Flask app together.

FastMCP's Streamable HTTP transport is ASGI; the existing CNS Vault web app is
WSGI (Flask). They share one Railway domain, so the **outer app is ASGI** and
the Flask app is mounted *inside* it via ``a2wsgi`` (the reverse — mounting
ASGI inside Flask/werkzeug ``DispatcherMiddleware`` — is not possible, since
that middleware is WSGI-only).

Routing:
  - The FastMCP app owns ``/mcp`` plus the OAuth discovery/proxy routes
    (``/.well-known/...``, ``/authorize``, ``/token``, ``/register``, ...),
    which must live at the domain root for claude.ai to discover them.
  - Everything else falls through to the Flask app (the catch-all ``Mount("/")``
    is appended last, so it never shadows the MCP/OAuth routes).

Run with an ASGI server (uvicorn worker), NOT plain sync-WSGI gunicorn:
    gunicorn app.asgi:asgi_app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
"""

from __future__ import annotations

import os

from a2wsgi import WSGIMiddleware
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.mcp_server import mcp
from app.server import app as flask_app

# The Flask (WSGI) app is the fall-through for every path the MCP/OAuth routes
# don't own. Wrapped once here so both code paths below reuse it.
_flask_fallthrough = Mount("/", app=WSGIMiddleware(flask_app))

# Fail closed: only expose /mcp when an OAuth provider is configured (or when a
# developer explicitly opts into an unauthenticated server locally). Otherwise a
# deploy without the OAuth env vars would publish an OPEN, data-mutating MCP
# endpoint (e.g. cortxt_close_issue / create_issue push to GitHub). Better to serve 503 there.
_auth_configured = mcp.auth is not None
_allow_insecure = os.getenv("MCP_ALLOW_INSECURE") == "1"

if _auth_configured or _allow_insecure:
    # NOTE: no global CORS middleware here. Starlette's CORSMiddleware hijacks
    # ALL preflight OPTIONS requests, so attaching it to this app (which also
    # serves the Flask routes via the fallthrough below) would 400 the
    # dashboard's cross-origin API preflights before they reach Flask's own
    # CORS handling. claude.ai calls /mcp server-side (no browser CORS needed),
    # so MCP doesn't require it. Flask keeps managing CORS for its own routes.
    #
    # stateless_http=True avoids per-session affinity. This is safe because
    # token state (JTI→user mapping) is persisted in Redis via client_storage,
    # and the JWT signing key is stable across restarts — so any worker can
    # validate any request regardless of which worker issued the token.
    mcp_app = mcp.http_app(path="/mcp", stateless_http=True)

    # Append Flask after the MCP/OAuth routes so it has lowest match priority.
    mcp_app.router.routes.append(_flask_fallthrough)

    # Lifespan comes from mcp_app (StarletteWithLifespan) and initialises the
    # Streamable HTTP session manager — required, or requests fail with
    # "Task group is not initialized".
    asgi_app = mcp_app
else:
    async def _mcp_unconfigured(request):
        return JSONResponse(
            {
                "error": "mcp_not_configured",
                "detail": (
                    "MCP server is disabled because OAuth is not configured. "
                    "Set MCP_GITHUB_CLIENT_ID, MCP_GITHUB_CLIENT_SECRET and "
                    "MCP_BASE_URL (or MCP_ALLOW_INSECURE=1 for local dev)."
                ),
            },
            status_code=503,
        )

    # Flask still works; /mcp is parked on a 503 stub instead of an open server.
    asgi_app = Starlette(
        routes=[
            Route("/mcp", _mcp_unconfigured, methods=["GET", "POST"]),
            _flask_fallthrough,
        ]
    )
