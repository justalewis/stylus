"""Stylize an article body via Claude using a per-journal style guide.

The journal's style guide (a Markdown file at
`content/journals/<slug>/template/style-guide.md`) describes the
editorial conventions: heading levels, Works Cited format, table
treatment, quote/dash/ellipsis preferences, what to fix, what to
preserve. Claude reads the style guide and the article body, then
returns a rewritten body that conforms to the guide.

The guarantees we ask Claude to honor:
  - Preserve content verbatim (no paraphrasing, no invention)
  - Preserve YAML front matter (we handle that separately)
  - Return ONLY the rewritten body, no explanations or fences

A single call replaces several smaller fixes:
  - Split run-on Works Cited entries
  - Strip Word/Mso HTML cruft
  - Normalize quotes and dashes per the guide
  - Repair broken tables and footnotes
  - Tighten paragraph structure

If `ANTHROPIC_API_KEY` isn't set or `anthropic` package is missing,
`available()` returns False and the button stays greyed out.

Cost: ~$0.02-$0.05 per typical article at Haiku 4.5 pricing (Apr 2026).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple


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
    import anthropic
    return anthropic.Anthropic()


def load_style_guide(journal_template_dir: Path) -> str:
    """Load the journal's style-guide.md. Returns empty string if
    not present (Claude then falls back to general MLA conventions)."""
    path = journal_template_dir / "style-guide.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def stylize(
    body_md: str,
    style_guide: str,
    *,
    article_title: str = "",
    max_output_tokens: int = 16000,
) -> Tuple[Optional[str], dict]:
    """Send article body + style guide to Claude. Returns (new_body, metadata).
    If Claude is unavailable, returns (None, {error: ...}).

    `body_md` is the article body WITHOUT YAML front matter — pass the
    `body` portion from `read_article_metadata`. The caller is
    responsible for writing the result back with the YAML preserved
    via `write_article_metadata`.

    metadata dict carries usage info: `input_tokens`, `output_tokens`,
    `estimated_cost_usd`, and `model`. Useful for transparency.
    """
    if not available():
        return None, {"error": "Claude API unavailable. Set ANTHROPIC_API_KEY and `pip install anthropic`."}

    system_prompt = (
        "You are an editorial stylist for a scholarly journal. You apply "
        "the journal's style guide to article manuscripts. Your job is to "
        "RESTRUCTURE FORMATTING only — never paraphrase, summarize, or "
        "invent content. Preserve every author's word, every citation, "
        "every URL exactly as given. The body is in Pandoc Markdown.\n\n"
        "RULES YOU MUST FOLLOW:\n"
        "1. Output ONLY the rewritten Markdown body. No preamble, no "
        "   explanations, no code fences.\n"
        "2. Preserve all content verbatim. Restructure only.\n"
        "3. Do not add or remove substantive text.\n"
        "4. Keep all citations, URLs, and footnote markers intact.\n"
        "5. If a section in the source is ambiguous or malformed, prefer "
        "   the journal's documented convention over inventing structure.\n"
        "6. Do NOT add YAML front matter — that's stripped before this "
        "   prompt and re-applied after."
    )

    if not style_guide:
        style_guide = (
            "(No journal-specific style guide provided. Apply general "
            "MLA 9 conventions: each Works Cited entry on its own "
            "paragraph; italicize book and journal titles; curly quotes "
            "for article titles; em-dashes for parenthetical breaks; "
            "convert Word HTML cruft to clean Markdown; preserve "
            "footnote markers as `[^N]` / `[^N]:`; preserve tables.)"
        )

    user_prompt = (
        f"# Journal style guide\n\n{style_guide}\n\n"
        f"---\n\n"
        f"# Article to stylize"
        f"{' (title: ' + article_title + ')' if article_title else ''}\n\n"
        f"```markdown\n{body_md}\n```\n\n"
        f"---\n\n"
        f"Apply the style guide to this article. Output the rewritten "
        f"Markdown body only — no code fence, no preamble."
    )

    msg = _client().messages.create(
        model=_MODEL,
        max_tokens=max_output_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text"))

    # Strip a possible code fence the model added against instructions.
    text = text.strip()
    if text.startswith("```"):
        # Drop the opening fence (may include a language tag).
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    text = text.strip()

    # Crude per-token costs (Haiku 4.5 pricing as of 2026 — adjust if
    # using a different model). Just for display, not billing.
    cost_in = msg.usage.input_tokens * 0.000001
    cost_out = msg.usage.output_tokens * 0.000005

    return text, {
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
        "estimated_cost_usd": round(cost_in + cost_out, 4),
        "model": _MODEL,
    }


__all__ = ["available", "load_style_guide", "stylize"]
