"""Heuristic Works-Cited prose → BibTeX converter.

This is a best-effort tool for editors who don't have a `.bib` file. The
user pastes a Works Cited list in MLA / APA / Chicago prose; we try to
extract author / year / title / container / publisher / pages / DOI /
URL and emit reasonable BibTeX entries. Anything we can't classify drops
into a `note` field so nothing is lost.

The output is meant to be edited; we make no claim of perfection. The
parser favors recall over precision — better to emit a slightly wrong
entry the user can fix than to drop the citation entirely.

Public entry points:
  - `parse_entries(text, style="mla")` → list[dict]
  - `to_bibtex(entries)` → str
  - `build_bib(text, style="mla")` → str  (convenience)
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Dict, Optional, Tuple


# -- regexes --------------------------------------------------------------

# A 4-digit year, optionally with letter suffix (e.g. "2024a").
_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})([a-z])?\b")
# DOI, in either bare or URL form.
_DOI_RE = re.compile(r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)(10\.\d{3,9}/[^\s)\"<>]+)", re.I)
# Generic URL.
_URL_RE = re.compile(r"https?://[^\s)\"<>]+")
# Page ranges: "pp. 123-145", "pp. 12--14", "123-45".
_PAGES_RE = re.compile(
    r"(?:pp?\.\s*)?(\d+\s*(?:[-–—]+\s*\d+)?)",
)
# MLA-style "vol. N, no. M".
_VOL_NO_RE = re.compile(r"vol\.?\s*(\d+(?:[._-]\d+)?)(?:[,\s]+no\.?\s*(\d+(?:[/&-]\d+)?))?", re.I)
# APA-style "12(3)" or "12 (3)".
_APA_VOL_NO_RE = re.compile(r"(?<![A-Za-z])(\d{1,4})\s*\((\d{1,4}(?:[/&-]\d+)?)\)")
# Chicago-style "57, no. 4" (no "vol." prefix).
_CHICAGO_VOL_NO_RE = re.compile(r"(?<![A-Za-z])(\d{1,4}),\s*no\.\s*(\d{1,4}(?:[/&-]\d+)?)", re.I)
# APA's parenthesized year, e.g. "Canagarajah, S. (2006). Title..."
_APA_YEAR_PAREN_RE = re.compile(r"\((\d{4})([a-z])?\)")
# Bare page-range that follows the volume/issue or sits at the entry tail.
_BARE_PAGES_RE = re.compile(r"(?:,\s*|:\s*)(\d{1,4}\s*[-–—]+\s*\d{1,4})(?=\s*[.,;]|\s*$)")
# Italic span in Markdown prose ("*Title*") — many editors paste from
# Word with smart-quote dashes intact, so we accept underscore too.
_ITALIC_RE = re.compile(r"(?<!\w)[*_]([^*_]{2,}?)[*_](?!\w)")
# A double-quoted span using straight or curly quotes.
_QUOTED_RE = re.compile(r"[“\"']([^”\"']{2,}?)[”\"']")


# -- normalization --------------------------------------------------------

def _normalize(text: str) -> str:
    """Smart quotes → straight, NFC, trim. We need the text in a stable
    form so the heuristics don't fight against typographic variants."""
    t = unicodedata.normalize("NFC", text)
    t = (
        t.replace("“", '"').replace("”", '"')
         .replace("‘", "'").replace("’", "'")
         .replace("–", "-").replace("—", "-")
         .replace(" ", " ")
    )
    return t


def _split_entries(text: str) -> List[str]:
    """Each Works Cited entry is one paragraph. Split on blank lines, then
    fall back to splitting on lines that look like entry starts if the
    whole thing was pasted as one blob."""
    text = _normalize(text).strip()
    if not text:
        return []
    # First: blank-line separated.
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1:
        return [re.sub(r"\s+", " ", b).strip() for b in blocks]
    # Single block: try to split on author-leading lines. An entry usually
    # starts with capitalized surname + comma, OR a repeat-author dash.
    parts: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        starts_new = bool(
            re.match(r"^([A-Z][\w'\-]+,\s+[A-Z]|---\.|—\.|--\.)", line)
        )
        if starts_new and current:
            parts.append(" ".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        parts.append(" ".join(current).strip())
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p]


# -- extraction helpers ---------------------------------------------------

def _extract_doi(text: str) -> Tuple[Optional[str], str]:
    m = _DOI_RE.search(text)
    if not m:
        return None, text
    doi = m.group(1).rstrip(".,;)")
    return doi, text[:m.start()] + text[m.end():]


def _extract_url(text: str) -> Tuple[Optional[str], str]:
    m = _URL_RE.search(text)
    if not m:
        return None, text
    url = m.group(0).rstrip(".,;)")
    return url, text[:m.start()] + text[m.end():]


def _extract_year(text: str) -> Tuple[Optional[str], Optional[str], str]:
    """Return (year, year_suffix, text_without). We pick the first 4-digit
    year that's actually plausible (1500–2199). APA's `(YEAR)` paren form
    is consumed whole so the empty parens don't pollute downstream parsing."""
    m = _APA_YEAR_PAREN_RE.search(text)
    if m:
        return m.group(1), m.group(2), text[:m.start()] + " " + text[m.end():]
    m = _YEAR_RE.search(text)
    if not m:
        return None, None, text
    year = m.group(1)
    suffix = m.group(2)
    rest = text[:m.start()] + text[m.end():]
    return year, suffix, rest


def _extract_italic(text: str) -> Tuple[Optional[str], str]:
    m = _ITALIC_RE.search(text)
    if not m:
        return None, text
    title = m.group(1).strip(" .,")
    rest = text[:m.start()] + " " + text[m.end():]
    return title, rest


def _extract_quoted(text: str) -> Tuple[Optional[str], str]:
    m = _QUOTED_RE.search(text)
    if not m:
        return None, text
    title = m.group(1).strip(" .,")
    rest = text[:m.start()] + " " + text[m.end():]
    return title, rest


def _extract_vol_issue_pages(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    """Return (volume, issue, pages, rest). Tries MLA, Chicago, then APA."""
    vol = issue = pages = None
    for pattern in (_VOL_NO_RE, _CHICAGO_VOL_NO_RE, _APA_VOL_NO_RE):
        m = pattern.search(text)
        if m:
            vol = m.group(1)
            issue = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            text = text[:m.start()] + " " + text[m.end():]
            break
    # Pages: look for pp. N-M first, then bare N-M near the tail.
    m = re.search(r"(?:pp?\.\s*)(\d+(?:\s*[-–—]+\s*\d+)?)", text)
    if m:
        pages = m.group(1).replace(" ", "")
        text = text[:m.start()] + text[m.end():]
    else:
        m = _BARE_PAGES_RE.search(text)
        if m:
            pages = m.group(1).replace(" ", "")
            text = text[:m.start()] + text[m.end():]
    return vol, issue, pages, text


# -- author parsing -------------------------------------------------------

def _parse_authors(authors_str: str) -> str:
    """Convert a prose author span into BibTeX `and`-joined form.

    Handles:
      - "Smith, John."
      - "Smith, John, and Jane Doe."
      - "Smith, John, et al."
      - "Smith, J. A., J. B. Doe, and K. C. Lee."  (APA)
      - "---" (placeholder for repeat author; we leave that to the caller)
    """
    s = authors_str.strip().rstrip(".,;:")
    if not s:
        return ""
    if s.startswith(("---", "—", "--")):
        return ""  # caller should reuse previous entry's authors
    # Strip "et al." and remember it so we can re-append.
    et_al = False
    s_clean = re.sub(r",?\s*et\s+al\.?\s*$", "", s, flags=re.I)
    if s_clean != s:
        et_al = True
        s = s_clean.strip().rstrip(",")
    # Authors are separated by "and" or ", and" (final pair) and "," (rest).
    # Strategy: find ", and " / " and " (case insensitive) → split into N
    # parts. The first part may be "Last, First" form; subsequent parts in
    # MLA are "First Last" (already normal order).
    parts = re.split(r"\s*,?\s+and\s+", s, flags=re.I)
    if len(parts) == 1:
        # No "and" — but APA lists multiple authors with "," separator and
        # an ampersand before the last. Try that.
        parts = re.split(r"\s*,?\s*&\s*", s)
    if len(parts) == 1:
        # Still one part. If it contains multiple commas, it might be MLA's
        # "Last, First, Last, First" or APA's "Last, F. M., Last, F. M."
        # Heuristic: every pair of comma-separated tokens is one author.
        tokens = [t.strip() for t in s.split(",") if t.strip()]
        if len(tokens) >= 4 and len(tokens) % 2 == 0:
            paired = []
            for i in range(0, len(tokens), 2):
                paired.append(f"{tokens[i]}, {tokens[i+1]}")
            parts = paired

    bib_authors: List[str] = []
    for i, p in enumerate(parts):
        p = p.strip(" .,;:")
        if not p:
            continue
        if "," in p and i == 0:
            # First author already "Last, First" — keep as-is.
            bib_authors.append(p)
        elif "," in p and i > 0 and re.match(r"^[A-Z][\w'\-]+,\s*[A-Z]", p):
            # Subsequent author in "Last, First" form (APA).
            bib_authors.append(p)
        elif " " in p:
            # "First Last" form (MLA subsequent author). Flip to "Last, First".
            words = p.split()
            last = words[-1]
            firsts = " ".join(words[:-1])
            bib_authors.append(f"{last}, {firsts}")
        else:
            bib_authors.append(p)

    if et_al:
        bib_authors.append("others")
    return " and ".join(bib_authors)


# -- entry classification -------------------------------------------------

def _guess_type(parsed: Dict) -> str:
    """Pick a BibTeX type based on what we extracted.

    Rules of thumb:
      - has journal AND vol/issue → @article  (MLA, APA, Chicago article)
      - has booktitle (italic container, no vol) → @incollection (chapter)
      - has italic title AND no container → @book
      - has URL/DOI and no container → @misc
      - default → @misc
    """
    has_journal = bool(parsed.get("journal"))
    has_booktitle = bool(parsed.get("booktitle"))
    has_vol = bool(parsed.get("volume"))
    has_url = bool(parsed.get("url") or parsed.get("doi"))
    title_source = parsed.get("_title_source")

    if has_journal and (has_vol or has_url):
        return "article"
    if has_journal:
        return "article"
    if has_booktitle:
        return "incollection"
    if title_source == "italic" and not has_journal and not has_booktitle:
        return "book"
    if has_url and not has_journal and not has_booktitle:
        return "misc"
    return "misc"


# -- key generation -------------------------------------------------------

def _slugify_key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9]+", "", s)
    return s or "ref"


def _make_key(parsed: Dict, used: set) -> str:
    # FirstAuthorLastNameYear  (e.g., "smith2024")
    authors = parsed.get("author", "")
    first = authors.split(" and ")[0] if authors else ""
    last = first.split(",")[0].strip() if "," in first else first.strip()
    last = _slugify_key(last).lower() or "ref"
    year = parsed.get("year") or "n.d."
    base = f"{last}{year}"
    key = base
    n = 0
    while key in used:
        n += 1
        key = f"{base}{chr(ord('a') + n - 1)}"  # smith2024a, smith2024b, ...
    used.add(key)
    return key


# -- parsing per-entry ----------------------------------------------------

def parse_entry(prose: str, style: str = "mla", prev_authors: Optional[str] = None) -> Dict:
    """Parse a single Works Cited entry into a dict of BibTeX fields."""
    text = _normalize(prose).strip()
    out: Dict = {"_raw": prose.strip()}

    # 1. Extract DOI and URL (off to the side so they don't confuse the
    # title/container extraction).
    doi, text = _extract_doi(text)
    if doi:
        out["doi"] = doi
    url, text = _extract_url(text)
    if url:
        out["url"] = url

    # 2. Year (and suffix).
    year, year_suffix, text = _extract_year(text)
    if year:
        out["year"] = year
        if year_suffix:
            out["_year_suffix"] = year_suffix

    # 3. Italic span → book title or container.
    italic, text = _extract_italic(text)
    # 4. Quoted span → article/chapter title.
    quoted, text = _extract_quoted(text)

    # 5. Vol / issue / pages.
    vol, issue, pages, text = _extract_vol_issue_pages(text)
    if vol:
        out["volume"] = vol
    if issue:
        out["number"] = issue
    if pages:
        out["pages"] = pages.replace("-", "--")

    # 6. Author(s) — the first chunk before the first ".  " separator.
    # If the entry begins with "---." it's a repeat-author placeholder.
    author_part = ""
    if re.match(r"^\s*(---\.|—\.|--\.)", text):
        author_part = prev_authors or ""
        text = re.sub(r"^\s*(---\.|—\.|--\.)\s*", "", text)
    else:
        m = re.match(r"^(.*?)\.(\s|$)", text)
        if m:
            author_part = m.group(1)
            text = text[m.end():].strip()
        else:
            # No period in the entry; punt and grab everything up to the
            # first ", and" pair, or just the first two tokens.
            author_part = text.split(",")[0]
    if author_part:
        bib_authors = _parse_authors(author_part)
        if bib_authors:
            out["author"] = bib_authors

    # 7. Title vs container.
    if quoted and italic:
        out["title"] = quoted
        out["_title_source"] = "quoted"
        if out.get("volume"):
            out["journal"] = italic
        else:
            out["booktitle"] = italic
    elif italic and out.get("volume") and not quoted:
        # APA article pattern: unquoted title + italic journal + vol/issue.
        # Italic is the container; title comes from the leftover prose
        # between the year and the journal title (or just the longest
        # remaining sentence).
        out["journal"] = italic
        leftover = text.strip(" .,;:")
        # Strip stray punctuation, double-spaces, isolated commas.
        leftover = re.sub(r"\s+", " ", leftover)
        leftover = re.sub(r"\s*,\s*,", ",", leftover).strip(" .,;:")
        if leftover:
            # Pick the longest "sentence" — most likely the title.
            sentences = [s.strip() for s in re.split(r"\.\s+", leftover) if s.strip()]
            if sentences:
                chosen = max(sentences, key=len)
                # Reject if it's all punctuation/digits.
                if re.search(r"[A-Za-z]{3,}", chosen):
                    out["title"] = chosen.rstrip(" .")
                    out["_title_source"] = "leftover"
                    # Strip the chosen title from `text` so it doesn't
                    # also end up in the catch-all note field.
                    text = text.replace(chosen, " ", 1)
    elif italic and not quoted:
        out["title"] = italic
        out["_title_source"] = "italic"
    elif quoted and not italic:
        out["title"] = quoted
        out["_title_source"] = "quoted"
    else:
        # Nothing matched. Try the leftover text: the next sentence is
        # often the title.
        leftover = text.strip(" .,;:")
        if leftover:
            m = re.match(r"^([^.]+)\.", leftover)
            if m:
                out["title"] = m.group(1).strip()
                out["_title_source"] = "fallback"

    # 8. Publisher / address (book pattern: "Publisher, Year").
    if not out.get("journal") and not out.get("booktitle") and out.get("title"):
        # Look in `text` for "Publisher, YEAR" — the year has already been
        # extracted, but the publisher would be a word or two before where
        # the year was.
        # Easier: scan remaining text for tokens that look like a publisher
        # (capitalized words, end with "Press" / "Books" / "Publishing", etc).
        m = re.search(
            r"\b([A-Z][\w&'\-]*(?:\s+[A-Z][\w&'\-]*){0,5}\s+(?:Press|Books|Publishing|University Press|UP|Publishers|Inc\.?|Ltd\.?))\b",
            text,
        )
        if m:
            out["publisher"] = m.group(1).strip()
            text = text[:m.start()] + text[m.end():]

    # 9. Note (anything left over that mentions "translated by", "edited by",
    # or that we couldn't classify but seems substantive). Strip stray
    # punctuation islands so we don't preserve garbage like ", , ()."
    leftover = re.sub(r"\s+", " ", text)
    leftover = re.sub(r"[(){}\[\]]", " ", leftover)
    leftover = re.sub(r"\s*([,.;:])\s*([,.;:])+", r"\1", leftover)
    leftover = re.sub(r"\s+", " ", leftover).strip(" .,;:")
    # Require at least 12 chars AND substantive alphabetic content.
    if leftover and len(leftover) > 12 and len(re.findall(r"[A-Za-z]", leftover)) > 8:
        out["note"] = leftover

    # 10. Done.
    return out


# -- BibTeX rendering -----------------------------------------------------

def _escape_bibtex_value(v: str) -> str:
    return v.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")


def to_bibtex(entries: List[Dict]) -> str:
    used_keys: set = set()
    out_lines: List[str] = []
    for entry in entries:
        bib_type = _guess_type(entry)
        key = _make_key(entry, used_keys)
        out_lines.append(f"@{bib_type}{{{key},")
        # Stable field order.
        for field in ("author", "title", "journal", "booktitle", "year",
                       "volume", "number", "pages", "publisher", "address",
                       "doi", "url", "note"):
            val = entry.get(field)
            if not val:
                continue
            out_lines.append(f"  {field} = {{{_escape_bibtex_value(str(val))}}},")
        # Trim trailing comma on the last field.
        if out_lines[-1].endswith(","):
            out_lines[-1] = out_lines[-1][:-1]
        out_lines.append("}")
        out_lines.append("")
    return "\n".join(out_lines).strip() + "\n"


# -- public top-level -----------------------------------------------------

def parse_entries(text: str, style: str = "mla") -> List[Dict]:
    blocks = _split_entries(text)
    parsed: List[Dict] = []
    prev_authors: Optional[str] = None
    for block in blocks:
        entry = parse_entry(block, style=style, prev_authors=prev_authors)
        if entry.get("author"):
            prev_authors = entry["author"]
        parsed.append(entry)
    return parsed


def build_bib(text: str, style: str = "mla") -> str:
    return to_bibtex(parse_entries(text, style=style))


__all__ = ["parse_entries", "to_bibtex", "build_bib", "parse_entry"]
