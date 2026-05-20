"""Stage 2: deterministic Markdown cleanup passes.

Each pass is a pure function: (text, log) -> text. They are composed in
`run_all`. Every transformation is logged. Passes are idempotent: running
the full pipeline twice produces the same output.

When the user's working `clean.py` draft arrives, refine these passes
against it (they should converge in behavior, with this module being the
production refactor: testable, logged, idempotent).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import yaml


@dataclass
class CleanupLog:
    entries: List[str] = field(default_factory=list)

    def record(self, name: str, count: int, note: str = ""):
        if count == 0 and not note:
            return
        msg = f"  - {name}: {count} change(s)"
        if note:
            msg += f" ({note})"
        self.entries.append(msg)

    def add(self, line: str):
        self.entries.append(line)

    def render(self) -> str:
        return "\n".join(self.entries)


# ---------- individual passes ----------

def _strip_class_wrapper(text: str, classname: str) -> tuple[str, int]:
    """Strip `[...]{.classname}` wrappers, preserving the inner content.

    Handles nested brackets and multi-line spans by walking backward from
    each `]{.classname}` marker to find the matching `[`. Plain regex with
    `[^\\[\\]]` can't do this because real-world highlights routinely
    contain markdown links, internal `[bracket]` paraphrases, and span
    multiple lines.
    """
    marker = "]{." + classname + "}"
    out: list[str] = []
    i = 0
    count = 0
    n = len(text)
    while i < n:
        close = text.find(marker, i)
        if close == -1:
            out.append(text[i:])
            break
        depth = 1
        j = close - 1
        while j >= i and depth > 0:
            c = text[j]
            if c == "]":
                depth += 1
            elif c == "[":
                depth -= 1
            j -= 1
        if depth == 0:
            open_pos = j + 1
            inner = text[open_pos + 1: close]
            out.append(text[i:open_pos])
            out.append(inner)
            i = close + len(marker)
            count += 1
        else:
            out.append(text[i: close + len(marker)])
            i = close + len(marker)
    return "".join(out), count


def strip_highlighter_spans(text: str, log: CleanupLog) -> str:
    """Strip `[text]{.mark}` (Word highlighter annotation)."""
    new_text, count = _strip_class_wrapper(text, "mark")
    log.record("strip_highlighter_spans", count)
    return new_text


def strip_underline_spans(text: str, log: CleanupLog) -> str:
    """Strip `[text]{.underline}` (Word underline annotation, typically
    wrapping a URL inside a markdown link). The link itself stays intact
    and renders with the journal's link styling."""
    new_text, count = _strip_class_wrapper(text, "underline")
    log.record("strip_underline_spans", count)
    return new_text


def unescape_quoted_brackets(text: str, log: CleanupLog) -> str:
    """`\\[` -> `[` and `\\]` -> `]`. Pandoc over-escapes these."""
    n1 = text.count(r"\[")
    n2 = text.count(r"\]")
    text = text.replace(r"\[", "[").replace(r"\]", "]")
    log.record("unescape_quoted_brackets", n1 + n2)
    return text


def reassemble_heading_linebreaks(text: str, log: CleanupLog) -> str:
    r"""Merge multi-line headings separated by literal pipe or hard return.

    Pandoc emits Word's multi-line headings as e.g.::

        # First half \|Second half

    Or sometimes as two adjacent heading lines that should be one. We
    handle the explicit pipe form (most common); we leave the rare
    adjacent-heading form for hand-editing since auto-merging there has
    high false-positive risk.
    """
    pattern = re.compile(r"^(#{1,6}\s.+?)\s*\\?\|\s*(.+)$", re.MULTILINE)
    count = 0

    def _merge(m: re.Match) -> str:
        nonlocal count
        count += 1
        return f"{m.group(1)} {m.group(2)}"

    text = pattern.sub(_merge, text)
    log.record("reassemble_heading_linebreaks", count)
    return text


def strip_orphan_page_numbers(text: str, log: CleanupLog) -> str:
    """Drop a lone 1-3 digit number on its own line at end of file.

    Conservative: only the trailing tail of the document. A single number
    mid-text could be intentional (e.g., a list).
    """
    pattern = re.compile(r"\n+\s*\d{1,3}\s*\n?\s*\Z")
    new_text, count = pattern.subn("\n", text)
    log.record("strip_orphan_page_numbers", count)
    return new_text.rstrip() + "\n"


def normalize_dashes(text: str, log: CleanupLog) -> str:
    """Pandoc's `--smart` should handle this, but verify.

    Unicode em-dashes -> `---`, en-dashes -> `--`. (We keep ASCII so the
    Markdown round-trips cleanly; Pandoc's smart-typography on output
    will re-render them as Unicode in HTML/PDF.)
    """
    em = text.count("—")
    en = text.count("–")
    text = text.replace("—", "---").replace("–", "--")
    log.record("normalize_dashes", em + en, f"em={em} en={en}")
    return text


def normalize_smart_quotes(text: str, log: CleanupLog) -> str:
    """Leave Unicode curly quotes as-is; Pandoc handles them.

    This pass exists as an idempotent no-op placeholder so the pipeline
    surface is stable. If we discover the source consistently has
    straight quotes that need curling, do it here.
    """
    log.record("normalize_smart_quotes", 0, "no-op (pandoc default)")
    return text


# ---------- conservative list normalization ----------

_LIST_CUE_RE = re.compile(
    r"(?:the\s+(?:\w+\s+)?(?:stories|points|reasons|examples|cases)\s+(?:we\s+)?(?:focus|consider|examine|discuss)\s+(?:on\s+)?are[:.])\s*$",
    re.IGNORECASE,
)


def conservative_list_normalization(text: str, log: CleanupLog) -> str:
    """No-op for now. The spec calls for conservative behavior; without a
    library of real-world inputs the safe default is to leave lists alone
    and surface ambiguity to the editor in the in-browser pane.
    """
    log.record("conservative_list_normalization", 0, "no-op (manual review)")
    return text


# ---------- front-matter extraction ----------

@dataclass
class ExtractedFrontMatter:
    title: Optional[str] = None
    authors: List[dict] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    body_after_strip: str = ""


_AUTHOR_AFFIL_RE = re.compile(
    r"^(?P<name>.+?)\s*(?:—|–|---|--)\s*(?P<aff>.+)$"
)


def _is_author_affil_line(s: str) -> bool:
    return bool(_AUTHOR_AFFIL_RE.match(s.strip()))


def _skip_blanks(lines, i):
    while i < len(lines) and not lines[i].strip():
        i += 1
    return i


def extract_lics_front_matter(text: str) -> ExtractedFrontMatter:
    """Parse LiCS submission preamble.

    LiCS convention (from spec):

        [Title]                         (optional; absent in some submissions)
        [Author 1] — [Affiliation 1]
        [Author 2] — [Affiliation 2]
        Keywords
        [semicolon-separated list]
        Abstract
        [abstract paragraph]
        [first heading or body]

    Returns the parsed pieces plus the body with preamble stripped.
    """
    fm = ExtractedFrontMatter()
    lines = text.split("\n")
    i = _skip_blanks(lines, 0)
    if i >= len(lines):
        fm.body_after_strip = text
        return fm

    first = lines[i].strip()

    # Decide whether the first line is a title or an author.
    # If it has the author-affil shape, it's an author (no title in this preamble).
    # Otherwise, treat it as the title.
    if first.startswith("#"):
        fm.body_after_strip = "\n".join(lines[i:])
        return fm

    if not _is_author_affil_line(first):
        fm.title = first.lstrip("*_ ").rstrip("*_ ") or None
        i += 1

    # Authors: consume consecutive author-affil lines (blank lines between are OK).
    while True:
        j = _skip_blanks(lines, i)
        if j >= len(lines):
            i = j
            break
        cand = lines[j].strip()
        if cand.startswith("#"):
            i = j
            break
        if cand.lower() in {"keywords", "keyword", "abstract"}:
            i = j
            break
        m = _AUTHOR_AFFIL_RE.match(cand)
        if m:
            fm.authors.append(
                {"name": m.group("name").strip(), "affiliation": m.group("aff").strip()}
            )
            i = j + 1
            continue
        # Bare author name (no affiliation): accept only if we've already seen one,
        # to avoid grabbing a stray body line.
        if fm.authors and 1 <= len(cand.split()) <= 6:
            fm.authors.append({"name": cand, "affiliation": None})
            i = j + 1
            continue
        i = j
        break

    # Keywords block.
    i = _skip_blanks(lines, i)
    if i < len(lines) and lines[i].strip().lower().startswith("keyword"):
        i += 1
        kw_lines = []
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                if kw_lines:
                    break
                i += 1
                continue
            if line.lower() == "abstract" or line.startswith("#"):
                break
            kw_lines.append(line)
            i += 1
        raw_kw = " ".join(kw_lines)
        fm.keywords = [k.strip() for k in re.split(r"[;,]", raw_kw) if k.strip()]

    # Abstract block.
    i = _skip_blanks(lines, i)
    if i < len(lines) and lines[i].strip().lower() == "abstract":
        i += 1
        abs_lines = []
        while i < len(lines):
            line = lines[i]
            if line.lstrip().startswith("#"):
                break
            abs_lines.append(line)
            i += 1
        fm.abstract = "\n".join(abs_lines).strip() or None

    fm.body_after_strip = "\n".join(lines[i:]).lstrip("\n")
    return fm


def yaml_block(front_matter: dict) -> str:
    """Render YAML block with `---` fences, suitable for prepending to Markdown."""
    body = yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True, width=10_000)
    return f"---\n{body}---\n\n"


def build_yaml_front_matter(text: str, log: CleanupLog, issue_metadata: Optional[dict] = None) -> str:
    """Find LiCS-style preamble, extract, emit YAML front matter prefix.

    If `text` already starts with a YAML block, leave it alone (idempotence).
    """
    if text.lstrip().startswith("---\n"):
        log.record("build_yaml_front_matter", 0, "already has front matter")
        return text

    fm = extract_lics_front_matter(text)
    if not fm.title and not fm.authors:
        log.record("build_yaml_front_matter", 0, "no preamble detected")
        return text

    # External metadata (docx pre-scan, issue config) wins over body extraction:
    # external sources are semantically more authoritative than heuristic parsing.
    extra = dict(issue_metadata or {})

    payload: dict = {}
    title = extra.pop("title", None) or fm.title
    if title:
        payload["title"] = title
    if "subtitle" in extra:
        payload["subtitle"] = extra.pop("subtitle")
    if fm.authors:
        payload["author"] = [
            {k: v for k, v in a.items() if v is not None} for a in fm.authors
        ]
    if "author" in extra:
        payload["author"] = extra.pop("author")
    if fm.abstract:
        payload["abstract"] = fm.abstract
    if "abstract" in extra:
        payload["abstract"] = extra.pop("abstract")
    if fm.keywords:
        payload["keywords"] = fm.keywords
    if "keywords" in extra:
        payload["keywords"] = extra.pop("keywords")
    for k, v in extra.items():
        payload[k] = v

    out = yaml_block(payload) + fm.body_after_strip
    log.record(
        "build_yaml_front_matter",
        1,
        f"title={bool(fm.title)} authors={len(fm.authors)} keywords={len(fm.keywords)} abstract={bool(fm.abstract)}",
    )
    return out


# ---------- pipeline ----------

Pass = Callable[[str, CleanupLog], str]

DEFAULT_PASSES: List[Pass] = [
    strip_highlighter_spans,
    strip_underline_spans,
    unescape_quoted_brackets,
    reassemble_heading_linebreaks,
    conservative_list_normalization,
    strip_orphan_page_numbers,
    normalize_dashes,
    normalize_smart_quotes,
]


def run_all(
    text: str,
    issue_metadata: Optional[dict] = None,
    passes: Optional[List[Pass]] = None,
) -> tuple[str, CleanupLog]:
    """Run all cleanup passes followed by front-matter extraction.

    Returns (cleaned_text, log).
    """
    log = CleanupLog()
    log.add(f"# Cleanup pass log")
    log.add(f"Input length: {len(text):,} chars")

    chosen = passes if passes is not None else DEFAULT_PASSES
    for fn in chosen:
        text = fn(text, log)

    text = build_yaml_front_matter(text, log, issue_metadata=issue_metadata)

    log.add(f"Output length: {len(text):,} chars")
    return text, log
