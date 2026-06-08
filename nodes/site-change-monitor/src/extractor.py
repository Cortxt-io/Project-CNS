"""Extract meaningful text content from raw HTML.

Design choice: use BeautifulSoup to strip scripts, styles, nav, footer, etc.
and return clean text. No JS rendering -- that's a later slice.
"""

from bs4 import BeautifulSoup

# Tags that rarely contain meaningful page content
STRIP_TAGS = [
    "script", "style", "noscript", "iframe",
    "nav", "footer", "header",  # often boilerplate
    "svg", "img", "video", "audio",
]


def extract_text(html: str) -> str:
    """Return meaningful text from HTML, one line per text block."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise tags entirely
    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Get text, collapse runs of whitespace per line, drop empty lines
    lines = []
    for line in soup.get_text(separator="\n").splitlines():
        cleaned = " ".join(line.split())
        if cleaned:
            lines.append(cleaned)

    return "\n".join(lines)
