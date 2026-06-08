"""Perplexity API client for CNS node updates."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

API_ENDPOINT = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar"

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "system_prompt.md"


def _get_api_key() -> str:
    load_dotenv()
    key = os.getenv("PERPLEXITY_API_KEY", "")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "Perplexity API key not configured. "
            "Use local mode or connector mode, or add PERPLEXITY_API_KEY to .env."
        )
    return key


def send_update_request(
    node_content: str,
    instruction: str,
) -> str:
    """Send an update request to Perplexity and return the raw JSON string.

    Args:
        node_content: Full text of the current node .md file.
        instruction: Natural language instruction from the user.

    Returns:
        Raw JSON string from the API response.

    Raises:
        RuntimeError: On API errors or missing key.
    """
    api_key = _get_api_key()
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    user_message = (
        f"Here is the current node file:\n\n"
        f"```markdown\n{node_content}\n```\n\n"
        f"Instruction: {instruction}\n\n"
        f"Respond with a single JSON object matching the node schema."
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=60)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Perplexity API error {resp.status_code}: {resp.text}"
        )

    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        # Remove first and last lines (the fences)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    return content
