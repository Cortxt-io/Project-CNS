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

from a2wsgi import WSGIMiddleware
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from app.mcp_server import mcp
from app.server import app as flask_app

# CORS for browser-based MCP clients. Scoped to Claude origins so it never
# double-sets headers on the Flask routes (which manage their own CORS).
# Exposing Mcp-Session-Id is required for the Streamable HTTP handshake.
_cors = Middleware(
    CORSMiddleware,
    allow_origins=["https://claude.ai", "https://claude.com"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

# stateless_http=True avoids per-session affinity, so the server stays correct
# even if Railway runs more than one worker (no shared session store needed).
mcp_app = mcp.http_app(path="/mcp", stateless_http=True, middleware=[_cors])

# Mount the existing Flask (WSGI) app as the fall-through for all other paths.
# Appended after the MCP/OAuth routes so it has lowest matching priority.
mcp_app.router.routes.append(Mount("/", app=WSGIMiddleware(flask_app)))

# Lifespan comes from mcp_app (StarletteWithLifespan) and initialises the
# Streamable HTTP session manager — required, or requests fail with
# "Task group is not initialized".
asgi_app = mcp_app
