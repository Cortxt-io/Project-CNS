"""ASGI entrypoint — serves the Flask app.

The MCP server was removed on 2026-07-13: 10 fat tools plus 43 aliases were exposed and **not one
was ever called** in any transcript. It carried OAuth, a Redis token store and a lease layer to
guard mutations nobody made.

The app stays ASGI-shaped because Railway's start command runs a uvicorn worker
(``gunicorn app.asgi:asgi_app -k uvicorn.workers.UvicornWorker``), and because the WSGI Flask app
cannot host ASGI. Starlette wraps it via ``a2wsgi``; the mount is the whole routing table now.

Run:
    gunicorn app.asgi:asgi_app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
"""

from __future__ import annotations

from a2wsgi import WSGIMiddleware
from starlette.applications import Starlette
from starlette.routing import Mount

from app.server import app as flask_app

asgi_app = Starlette(routes=[Mount("/", app=WSGIMiddleware(flask_app))])
