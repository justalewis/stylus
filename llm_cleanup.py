"""Opt-in LLM-assisted cleanup pass using the Anthropic Claude API.

This module is intentionally *narrow* in what it asks the model to do:
each public function takes a specific kind of broken content and asks
Claude to reconstruct it, with strict guardrails so we don't get
hallucinated content swapped in for what the author actually wrote.

Available only when:
  - `anthropic` Python package is installed (`pip install anthropic`)
  - `ANTHROPIC_API_KEY` env var is set

If either is missing, every function here is a no-op that returns the
input unchanged. Callers should always handle that case.

Use cases:
  - `repair_mangled_table(md)`: take a busted grid table and ask Claude
    to emit a clean pipe table preserving the data.
  - `generate_alt_text(image_path)`: take an image and return a 1-2
    sentence alt text description (accessibility win).
  - `polish_paragraph(text)`: take a paragraph that looks OCR'd or
    Pandoc-mangled (broken hyphens, runs-on, etc.) and clean it up.

All calls are bounded — short input, short output — to keep cost
predictable. Typical cost: $0.001–$0.01 per call at current rates.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_MODEL = os.environ.get("GRAPHION_CLAUDE_MODEL", "claude-haiku-4-5")


def available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except Exception:
        return False


def _client():
    """Lazily construct the Anthropic client. Caller must check
    `available()` first."""
    import anthropic
    return anthropic.Anthropic()


def repair_mangled_table(md_table: str, context: str = "") -> Optional[str]:
    """Given a mangled grid table, return a clean Markdown pipe table.

    `context` is optional surrounding prose to help Claude understand
    what the table is about. Returns None if LLM is unavailable.
    """
    if not available():
        return None
    prompt = (
        "Below is a damaged Markdown grid table that lost its structure "
        "during a DOCX→Markdown conversion. Reconstruct it as a clean "
        "Markdown pipe table. Preserve every cell's data verbatim — do "
        "not summarize, paraphrase, or invent content. If a cell is "
        "empty, leave it empty. Output ONLY the pipe table, no preamble "
        "or explanation.\n\n"
        f"Context (surrounding prose, for understanding the table's "
        f"purpose):\n{context[:500] if context else '(none)'}\n\n"
        f"Damaged table:\n```\n{md_table}\n```\n"
    )
    msg = _client().messages.create(
        model=_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text"))
    # Strip code fence if present.
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def generate_alt_text(image_path: Path, surrounding_text: str = "") -> Optional[str]:
    """Generate alt text for an image. Uses Claude's vision capability.
    Returns None if LLM is unavailable or the image type is unsupported.
    """
    if not available():
        return None
    if not image_path.exists():
        return None
    suffix = image_path.suffix.lower().lstrip(".")
    # Claude vision supports png, jpg, gif, webp.
    mime_map = {"png": "image/png", "jpg": "image/jpeg",
                "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
    media_type = mime_map.get(suffix)
    if not media_type:
        return None
    import base64
    data = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    prompt = (
        "Generate a brief (1-2 sentence) alt text description for this "
        "image suitable for a scholarly article. Describe what is "
        "visually present and any data shown. Do not start with "
        "'Image of' or 'Picture of'. Be concrete and concise.\n\n"
        f"Surrounding article text for context:\n"
        f"{surrounding_text[:500] if surrounding_text else '(none)'}"
    )
    msg = _client().messages.create(
        model=_MODEL,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type, "data": data,
                }},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text"))
    return text.strip().strip('"').strip()


def polish_paragraph(text: str) -> Optional[str]:
    """Take a paragraph with OCR-style artifacts (broken hyphens,
    misplaced spaces, weird line breaks) and clean it up. Preserves
    semantic content; only fixes formatting. Returns None if LLM
    unavailable."""
    if not available():
        return None
    if len(text) < 30 or len(text) > 4000:
        return text  # too small to bother / too large to risk
    prompt = (
        "Below is a paragraph from a scholarly article that may have "
        "OCR-style artifacts: broken hyphens at line ends, doubled "
        "spaces, misplaced commas, missing word breaks. Fix only the "
        "formatting issues. Do NOT paraphrase, summarize, or rewrite "
        "the meaning. Preserve every quotation, citation, and proper "
        "noun verbatim. Output ONLY the corrected paragraph, no "
        "explanation.\n\n"
        f"Paragraph:\n{text}\n"
    )
    msg = _client().messages.create(
        model=_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if hasattr(b, "text")).strip()


__all__ = [
    "available",
    "repair_mangled_table",
    "generate_alt_text",
    "polish_paragraph",
]
