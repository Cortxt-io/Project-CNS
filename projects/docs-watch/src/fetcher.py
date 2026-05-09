"""Fetch raw HTML from a URL."""

import requests


def fetch_html(url: str, timeout: int = 15) -> str:
    """Fetch and return raw HTML. Raises on HTTP errors."""
    headers = {
        "User-Agent": "DocsWatch/0.1 (changelog-monitor bot)",
        "Accept": "text/html",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text
