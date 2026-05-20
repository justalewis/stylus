"""Phase 1 smoke test driver.

Runs the full pipeline against the Fernandes DOCX without going through
the Flask layer. Prints what each stage produced and where to find it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import conversion
import db
import seed
from config import CONTENT_DIR

SOURCE = Path("_dropbox/FernandesSanoFranchiniMcIntyre-Formatted.docx")
SLUG = "fernandes-sanofranchini-mcintyre-2026"
JOURNAL_SLUG = "lics"


def main():
    db.init_db()
    seed.ensure_lics_journal()

    journal = db.query_one("SELECT * FROM journals WHERE slug = ?", (JOURNAL_SLUG,))
    if not journal:
        print("! LiCS journal not seeded", file=sys.stderr)
        sys.exit(1)

    if not SOURCE.exists():
        print(f"! Source DOCX missing: {SOURCE}", file=sys.stderr)
        sys.exit(1)

    existing = db.query_one(
        "SELECT id FROM articles WHERE journal_id = ? AND slug = ?",
        (journal["id"], SLUG),
    )
    if existing:
        print(f"  article {SLUG!r} already exists (id={existing['id']}); reusing")
        article_id = existing["id"]
    else:
        apath = conversion.article_dir(JOURNAL_SLUG, None, SLUG)
        article_id = db.execute(
            "INSERT INTO articles (journal_id, slug, title, project_path, status) "
            "VALUES (?, ?, ?, ?, 'draft')",
            (journal["id"], SLUG, "Fernandes / Sano-Franchini / McIntyre (placeholder)", str(apath)),
        )
        print(f"  created article record id={article_id}")

    article = db.query_one("SELECT * FROM articles WHERE id = ?", (article_id,))
    apath = Path(article["project_path"])
    print(f"  project dir: {apath}")

    print("\n[Stage 1] DOCX ingest...")
    res = conversion.ingest_docx(SOURCE, apath, accept_track_changes=True)
    print(f"  raw md: {res.raw_md_path}  ({res.raw_md_path.stat().st_size:,} bytes)")
    print(f"  tracked changes present: {res.has_tracked_changes}")

    print("\n[Stage 2] Cleanups...")
    cleaned = conversion.run_cleanups(apath)
    print(f"  cleaned: {cleaned}  ({cleaned.stat().st_size:,} bytes)")

    print("\n[Stage 4] Render...")
    result = conversion.render_all(apath, JOURNAL_SLUG)
    print(f"  html: {result.html_path}")
    print(f"  pdf:  {result.pdf_path}")
    if result.errors:
        print("  errors:")
        for e in result.errors:
            print(f"    {e}")

    conversion.record_conversion(
        article_id, "docx",
        f"smoketest pipeline OK; html={bool(result.html_path)} pdf={bool(result.pdf_path)}",
        success=not result.errors,
    )

    print("\nDone.")
    print(f"  Conversion log: {apath/'conversion.log'}")


if __name__ == "__main__":
    main()
