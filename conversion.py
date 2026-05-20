"""Conversion pipeline. Wraps Stages 1, 3, and 4 of the spec.

Stage 2 (cleanups) is in `cleanups.py` and called from here.
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pypandoc

import cleanups
import db
from config import CONTENT_DIR, VERSIONS_KEEP


# ---------- helpers ----------

def article_dir(journal_slug: str, issue_slug: Optional[str], article_slug: str) -> Path:
    if issue_slug:
        d = CONTENT_DIR / "journals" / journal_slug / "issues" / issue_slug / "articles" / article_slug
    else:
        d = CONTENT_DIR / "journals" / journal_slug / "_unfiled" / article_slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "assets").mkdir(exist_ok=True)
    (d / ".versions").mkdir(exist_ok=True)
    return d


def template_dir(journal_slug: str) -> Path:
    return CONTENT_DIR / "journals" / journal_slug / "template"


def _append_log(article_path: Path, header: str, body: str):
    log_file = article_path / "conversion.log"
    stamp = datetime.now().isoformat(timespec="seconds")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"\n=== {stamp}  {header} ===\n{body}\n")


def _pandoc_version() -> str:
    try:
        return pypandoc.get_pandoc_version()
    except Exception:
        return "unknown"


def _snapshot_version(article_path: Path):
    """Save current article.md to .versions/ before overwrite. Keep last N."""
    src = article_path / "article.md"
    if not src.exists():
        return
    versions_dir = article_path / ".versions"
    versions_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    shutil.copy2(src, versions_dir / f"article-{stamp}.md")
    snaps = sorted(versions_dir.glob("article-*.md"))
    while len(snaps) > VERSIONS_KEEP:
        snaps.pop(0).unlink(missing_ok=True)


# ---------- Stage 1: DOCX ingest ----------

@dataclass
class IngestResult:
    raw_md_path: Path
    log: str
    has_tracked_changes: bool


def ingest_docx(
    docx_path: Path,
    article_path: Path,
    accept_track_changes: bool = True,
) -> IngestResult:
    """Run Pandoc on the DOCX, extract media, write `article-raw.md`.

    Before invoking Pandoc, scan the docx for a `Title`-styled paragraph
    (Pandoc does not promote that style to a markdown heading). When
    found, inject it as Pandoc metadata so the raw markdown opens with
    a YAML front matter block.
    """
    article_path.mkdir(parents=True, exist_ok=True)
    assets = article_path / "assets"
    assets.mkdir(exist_ok=True)

    source_copy = article_path / "source.docx"
    if Path(docx_path).resolve() != source_copy.resolve():
        shutil.copy2(docx_path, source_copy)

    raw_md = article_path / "article-raw.md"

    docx_title = _extract_docx_title(source_copy)

    extra = [
        "--wrap=none",
        "--markdown-headings=atx",
        f"--extract-media={assets}",
        f"--track-changes={'accept' if accept_track_changes else 'reject'}",
    ]

    t0 = time.time()
    pypandoc.convert_file(
        str(source_copy),
        to="markdown",
        format="docx",
        outputfile=str(raw_md),
        extra_args=extra,
    )
    dt = time.time() - t0

    has_tracked = _docx_has_tracked_changes(source_copy)

    body = (
        f"pandoc version: {_pandoc_version()}\n"
        f"input: {source_copy.name}\n"
        f"output: {raw_md.name}\n"
        f"extract-media: {assets.relative_to(article_path)}\n"
        f"track-changes: {'accept' if accept_track_changes else 'reject'}\n"
        f"tracked-changes-present: {has_tracked}\n"
        f"docx-title-detected: {docx_title or '(none)'}\n"
        f"elapsed: {dt:.2f}s\n"
    )
    _append_log(article_path, "Stage 1: DOCX ingest", body)

    return IngestResult(raw_md_path=raw_md, log=body, has_tracked_changes=has_tracked)


def _extract_docx_title(docx_path: Path) -> Optional[str]:
    """Pull the title from the docx Title-styled paragraph or core properties."""
    try:
        import docx as _docx
        d = _docx.Document(str(docx_path))
    except Exception:
        return None

    core_title = (d.core_properties.title or "").strip()
    if core_title:
        return core_title

    for p in d.paragraphs[:20]:
        style = (p.style.name if p.style else "") or ""
        text = p.text.strip()
        if not text:
            continue
        if style.lower() in {"title", "document title", "subtitle"} and style.lower() != "subtitle":
            return text.replace("\n", " ").strip()
        if style.lower() == "title":
            return text
    return None


def _docx_has_tracked_changes(docx_path: Path) -> bool:
    """Quick heuristic: unzip docx and check for w:ins / w:del tags."""
    import zipfile
    try:
        with zipfile.ZipFile(docx_path) as z:
            if "word/document.xml" not in z.namelist():
                return False
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
            return ("<w:ins " in xml) or ("<w:del " in xml)
    except Exception:
        return False


# ---------- Stage 2 orchestration ----------

def run_cleanups(article_path: Path, issue_metadata: Optional[dict] = None) -> Path:
    """Read article-raw.md, apply cleanups, write article.md. Snapshot first.

    Pulls the docx title from source.docx if present and merges it into
    the YAML front matter (Pandoc's markdown writer does not promote
    Word's Title style to anything recoverable from the body alone).
    """
    raw = (article_path / "article-raw.md").read_text(encoding="utf-8")

    extra_metadata = dict(issue_metadata or {})
    source_docx = article_path / "source.docx"
    if source_docx.exists() and "title" not in extra_metadata:
        title = _extract_docx_title(source_docx)
        if title:
            extra_metadata["title"] = title

    cleaned, log = cleanups.run_all(raw, issue_metadata=extra_metadata)

    _snapshot_version(article_path)
    (article_path / "article.md").write_text(cleaned, encoding="utf-8")
    _append_log(article_path, "Stage 2: cleanups", log.render())
    return article_path / "article.md"


def save_markdown(article_path: Path, new_text: str, note: str = "manual edit"):
    """Editor save. Snapshots the previous version."""
    _snapshot_version(article_path)
    (article_path / "article.md").write_text(new_text, encoding="utf-8")
    _append_log(article_path, "Stage 3: editor save", f"note: {note}\nbytes: {len(new_text)}")


# ---------- metadata helpers ----------

# Canonical YAML field order. Keys outside this list are appended after.
_FIELD_ORDER = (
    "title", "subtitle",
    "author",
    "abstract",
    "keywords",
    "short-title", "short-authors",
    "doi",
    "journal", "issn", "volume", "issue", "year",
    "start-page", "end-page",
    "submitted-date", "accepted-date", "published-date",
    "copyright",
    "status",
)


def read_article_metadata(article_path: Path) -> tuple[dict, str]:
    """Return (front_matter_dict, body_string) from article.md.

    If no YAML front matter is present, returns ({}, full_text).
    """
    import yaml
    md_path = article_path / "article.md"
    text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body_start = end + len("\n---")
    if text[body_start:body_start + 1] == "\n":
        body_start += 1
    try:
        fm = yaml.safe_load(raw) or {}
    except Exception:
        fm = {}
    return fm, text[body_start:]


def write_article_metadata(article_path: Path, fm: dict, body: str | None = None):
    """Write article.md with the given front matter and body. Snapshots first.

    If `body` is None, preserves the current body. Field order is canonical
    (title first, then authors, etc.) so files diff cleanly between saves.
    """
    import yaml
    if body is None:
        _, body = read_article_metadata(article_path)

    ordered: dict = {}
    for k in _FIELD_ORDER:
        if k in fm and fm[k] not in (None, "", []):
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered and v not in (None, "", []):
            ordered[k] = v

    yaml_text = yaml.safe_dump(
        ordered, sort_keys=False, allow_unicode=True, width=10_000, default_flow_style=False
    )
    out_text = f"---\n{yaml_text}---\n\n{body.lstrip(chr(10))}"

    _snapshot_version(article_path)
    (article_path / "article.md").write_text(out_text, encoding="utf-8")
    _append_log(
        article_path,
        "Stage 3: metadata save",
        f"fields: {', '.join(ordered.keys())}\nbytes: {len(out_text)}",
    )


# ---------- Stage 4: render ----------

@dataclass
class RenderResult:
    html_path: Optional[Path]
    pdf_path: Optional[Path]
    errors: list


def render_html(article_path: Path, journal_slug: str) -> Path:
    md = article_path / "article.md"
    out = article_path / "article.html"
    tpl = template_dir(journal_slug)
    template = tpl / "article.html.j2"
    css = tpl / "article.css"
    lua_filter = tpl / "lics-filter.lua"

    extra = [
        "--standalone",
        "--section-divs",
        f"--template={template}",
        f"--css={css.name}",
    ]
    if lua_filter.exists():
        extra.append(f"--lua-filter={lua_filter}")

    if css.exists():
        shutil.copy2(css, article_path / css.name)

    pypandoc.convert_file(
        str(md),
        to="html5",
        format="markdown+yaml_metadata_block",
        outputfile=str(out),
        extra_args=extra,
    )
    return out


def render_pdf(article_path: Path, journal_slug: str) -> Path:
    """Render PDF via Pandoc (Typst template) + typst-py compile.

    Pandoc reads article.md, substitutes YAML front matter into the
    journal's Pandoc Typst template, and writes article.typ. The typst
    Python package then compiles that to article.pdf.
    """
    md = article_path / "article.md"
    out = article_path / "article.pdf"
    tpl = template_dir(journal_slug)
    typ_template = tpl / "article.typ"
    lua_filter = tpl / "lics-filter.lua"
    typst_input = article_path / "article.typ"

    extra = [f"--template={typ_template}"]
    if lua_filter.exists():
        extra.append(f"--lua-filter={lua_filter}")
    pypandoc.convert_file(
        str(md),
        to="typst",
        format="markdown+yaml_metadata_block",
        outputfile=str(typst_input),
        extra_args=extra,
    )

    import typst as typst_lib
    typst_lib.compile(str(typst_input), output=str(out))
    return out


def render_all(article_path: Path, journal_slug: str) -> RenderResult:
    errors = []
    html_path = pdf_path = None
    try:
        html_path = render_html(article_path, journal_slug)
    except Exception as exc:
        errors.append(f"HTML: {type(exc).__name__}: {exc}")
    try:
        pdf_path = render_pdf(article_path, journal_slug)
    except Exception as exc:
        errors.append(f"PDF: {type(exc).__name__}: {exc}")

    body = json.dumps(
        {
            "html": str(html_path) if html_path else None,
            "pdf": str(pdf_path) if pdf_path else None,
            "errors": errors,
        },
        indent=2,
    )
    _append_log(article_path, "Stage 4: render", body)
    return RenderResult(html_path=html_path, pdf_path=pdf_path, errors=errors)


# ---------- DB integration ----------

def record_conversion(article_id: int, source_format: str, notes: str, success: bool = True):
    db.execute(
        "INSERT INTO conversions (article_id, source_format, pandoc_version, notes, success) "
        "VALUES (?, ?, ?, ?, ?)",
        (article_id, source_format, _pandoc_version(), notes, 1 if success else 0),
    )
