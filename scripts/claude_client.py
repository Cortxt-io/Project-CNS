"""Anthropic Claude API client for CNS project updates."""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "system_prompt.md"


def _get_api_key() -> str:
    load_dotenv()
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key == "your_key_here":
        raise RuntimeError(
            "Anthropic API key not configured. Add ANTHROPIC_API_KEY to .env."
        )
    return key


def send_update_request(
    project_content: str,
    instruction: str,
) -> str:
    """Send an update request to Claude and return the raw JSON string.

    Args:
        project_content: Full text of the current project .md file.
        instruction: Natural language instruction from the user.

    Returns:
        Raw JSON string from the API response.

    Raises:
        RuntimeError: On API errors or missing key.
    """
    api_key = _get_api_key()
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    user_message = (
        f"Here is the current project file:\n\n"
        f"```markdown\n{project_content}\n```\n\n"
        f"Instruction: {instruction}\n\n"
        f"Respond with a single JSON object matching the project schema."
    )

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        raise RuntimeError(
            f"Anthropic API error {exc.status_code}: {exc.message}"
        ) from exc

    content = response.content[0].text

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
