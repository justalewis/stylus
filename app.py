"""Flask app. Phase 1 routes: dashboard, upload, edit, render, download."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request,
    send_from_directory, url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

import conversion
import db
from auth import User, login_manager
from config import (
    ALLOWED_UPLOAD_EXTENSIONS, CONTENT_DIR, MAX_UPLOAD_BYTES, SECRET_KEY,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    db.init_db()
    login_manager.init_app(app)

    register_routes(app)
    return app


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "article"


def register_routes(app: Flask):

    # ---------- auth ----------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            user = User.by_username(request.form.get("username", ""))
            if user and user.check_password(request.form.get("password", "")):
                login_user(user, remember=True)
                return redirect(url_for("dashboard"))
            flash("Invalid credentials.", "error")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # ---------- dashboard ----------

    @app.route("/")
    @login_required
    def dashboard():
        journals = db.query_all("SELECT * FROM journals ORDER BY name")
        recent = db.query_all(
            "SELECT a.*, j.name AS journal_name "
            "FROM articles a JOIN journals j ON a.journal_id = j.id "
            "ORDER BY a.updated_at DESC LIMIT 20"
        )
        return render_template("dashboard.html", journals=journals, recent=recent)

    # ---------- journal ----------

    @app.route("/journals/<slug>")
    @login_required
    def journal_home(slug):
        j = db.query_one("SELECT * FROM journals WHERE slug = ?", (slug,))
        if not j:
            abort(404)
        articles = db.query_all(
            "SELECT * FROM articles WHERE journal_id = ? ORDER BY updated_at DESC",
            (j["id"],),
        )
        return render_template("journal.html", journal=j, articles=articles)

    # ---------- upload ----------

    @app.route("/journals/<slug>/upload", methods=["GET", "POST"])
    @login_required
    def upload_article(slug):
        journal = db.query_one("SELECT * FROM journals WHERE slug = ?", (slug,))
        if not journal:
            abort(404)

        if request.method == "POST":
            f = request.files.get("docx")
            slug_override = request.form.get("slug", "").strip()
            title_hint = request.form.get("title", "").strip()
            short_title = request.form.get("short_title", "").strip()
            short_authors = request.form.get("short_authors", "").strip()
            accept_tc = request.form.get("track_changes", "accept") == "accept"

            if not f or not f.filename:
                flash("No file uploaded.", "error")
                return redirect(request.url)
            if not short_title or not short_authors:
                flash("Short title and short authors are required for running headers.", "error")
                return redirect(request.url)

            filename = secure_filename(f.filename)
            if Path(filename).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS:
                flash("Only .docx files are accepted.", "error")
                return redirect(request.url)

            article_slug = slug_override or slugify(Path(filename).stem)
            existing = db.query_one(
                "SELECT id FROM articles WHERE journal_id = ? AND slug = ?",
                (journal["id"], article_slug),
            )
            if existing:
                flash(f"An article with slug {article_slug!r} already exists.", "error")
                return redirect(request.url)

            apath = conversion.article_dir(slug, None, article_slug)
            staged = apath / filename
            f.save(staged)

            try:
                conversion.ingest_docx(staged, apath, accept_track_changes=accept_tc)
                conversion.run_cleanups(
                    apath,
                    issue_metadata={
                        "short-title": short_title,
                        "short-authors": short_authors,
                    },
                )
            except Exception as exc:
                flash(f"Conversion failed: {exc}", "error")
                return redirect(request.url)

            title = title_hint or _peek_title(apath / "article.md") or article_slug
            article_id = db.execute(
                "INSERT INTO articles (journal_id, slug, title, project_path, status) "
                "VALUES (?, ?, ?, ?, 'draft')",
                (journal["id"], article_slug, title, str(apath)),
            )
            conversion.record_conversion(
                article_id, "docx",
                f"ingest + cleanups OK; project_path={apath}",
            )
            return redirect(url_for("article_home", article_id=article_id))

        return render_template("upload.html", journal=journal)

    # ---------- article ----------

    @app.route("/articles/<int:article_id>")
    @login_required
    def article_home(article_id):
        article = db.query_one(
            "SELECT a.*, j.slug AS journal_slug, j.name AS journal_name "
            "FROM articles a JOIN journals j ON a.journal_id = j.id WHERE a.id = ?",
            (article_id,),
        )
        if not article:
            abort(404)
        log_path = Path(article["project_path"]) / "conversion.log"
        log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        rendered_html = (Path(article["project_path"]) / "article.html").exists()
        rendered_pdf = (Path(article["project_path"]) / "article.pdf").exists()
        return render_template(
            "article.html",
            article=article,
            log_text=log_text,
            rendered_html=rendered_html,
            rendered_pdf=rendered_pdf,
        )

    @app.route("/articles/<int:article_id>/metadata", methods=["GET", "POST"])
    @login_required
    def article_metadata(article_id):
        article = db.query_one(
            "SELECT a.*, j.slug AS journal_slug, j.name AS journal_name "
            "FROM articles a JOIN journals j ON a.journal_id = j.id WHERE a.id = ?",
            (article_id,),
        )
        if not article:
            abort(404)
        apath = Path(article["project_path"])
        fm, body = conversion.read_article_metadata(apath)

        if request.method == "POST":
            updated = dict(fm)
            for key in (
                "title", "subtitle", "short-title", "short-authors", "footer",
                "doi", "abstract", "status", "copyright",
                "journal", "volume", "issue", "year",
            ):
                form_key = key.replace("-", "_")
                val = request.form.get(form_key, "").strip()
                if val:
                    updated[key] = val
                else:
                    updated.pop(key, None)

            page = request.form.get("start_page", "").strip()
            if page:
                try:
                    updated["start-page"] = int(page)
                except ValueError:
                    flash("Start page must be a number.", "error")
                    return redirect(request.url)
            else:
                updated.pop("start-page", None)

            kw_raw = request.form.get("keywords", "").strip()
            if kw_raw:
                updated["keywords"] = [
                    k.strip() for k in kw_raw.replace(";", ",").split(",") if k.strip()
                ]
            else:
                updated.pop("keywords", None)

            author_names = request.form.getlist("author_name")
            author_affils = request.form.getlist("author_affiliation")
            author_orcids = request.form.getlist("author_orcid")
            authors: list[dict] = []
            for i, name in enumerate(author_names):
                name = (name or "").strip()
                if not name:
                    continue
                rec: dict = {"name": name}
                aff = (author_affils[i] if i < len(author_affils) else "").strip()
                if aff:
                    rec["affiliation"] = aff
                orcid = (author_orcids[i] if i < len(author_orcids) else "").strip()
                if orcid:
                    rec["orcid"] = orcid
                authors.append(rec)
            if authors:
                updated["author"] = authors
            else:
                updated.pop("author", None)

            if not updated.get("title"):
                flash("Title is required.", "error")
                return redirect(request.url)
            if not updated.get("short-title") or not updated.get("short-authors"):
                flash("Short title and short authors are required for running headers.", "error")
                return redirect(request.url)

            conversion.write_article_metadata(apath, updated, body)
            if updated.get("title") != article["title"]:
                db.execute(
                    "UPDATE articles SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (updated["title"], article_id),
                )
            else:
                db.execute(
                    "UPDATE articles SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (article_id,),
                )

            render_result = conversion.render_all(apath, article["journal_slug"])
            if render_result.errors:
                flash(
                    "Metadata saved, but re-render had issues: " + "; ".join(render_result.errors),
                    "error",
                )
            else:
                flash("Metadata saved and re-rendered.", "success")
            return redirect(url_for("article_home", article_id=article_id))

        kw_string = ""
        if isinstance(fm.get("keywords"), list):
            kw_string = "; ".join(fm["keywords"])
        elif fm.get("keywords"):
            kw_string = str(fm["keywords"])

        authors_list = fm.get("author") or []
        if isinstance(authors_list, dict):
            authors_list = [authors_list]

        return render_template(
            "metadata.html",
            article=article,
            fm=fm,
            authors=authors_list,
            keywords_str=kw_string,
        )

    @app.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
    @login_required
    def article_edit(article_id):
        article = db.query_one("SELECT * FROM articles WHERE id = ?", (article_id,))
        if not article:
            abort(404)
        apath = Path(article["project_path"])
        md_path = apath / "article.md"

        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            new_text = payload.get("content", "")
            conversion.save_markdown(apath, new_text, note="editor save")
            db.execute(
                "UPDATE articles SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (article_id,),
            )
            return jsonify({"ok": True, "bytes": len(new_text)})

        md_text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        return render_template("edit.html", article=article, md_text=md_text)

    @app.route("/articles/<int:article_id>/render", methods=["POST"])
    @login_required
    def article_render(article_id):
        article = db.query_one(
            "SELECT a.*, j.slug AS journal_slug FROM articles a "
            "JOIN journals j ON a.journal_id = j.id WHERE a.id = ?",
            (article_id,),
        )
        if not article:
            abort(404)
        apath = Path(article["project_path"])
        result = conversion.render_all(apath, article["journal_slug"])
        return jsonify({
            "html": str(result.html_path) if result.html_path else None,
            "pdf": str(result.pdf_path) if result.pdf_path else None,
            "errors": result.errors,
        })

    @app.route("/articles/<int:article_id>/html")
    @login_required
    def serve_html(article_id):
        return _serve_artifact(article_id, "article.html")

    @app.route("/articles/<int:article_id>/pdf")
    @login_required
    def serve_pdf(article_id):
        return _serve_artifact(article_id, "article.pdf")

    @app.route("/articles/<int:article_id>/assets/<path:filename>")
    @login_required
    def serve_asset(article_id, filename):
        article = db.query_one("SELECT project_path FROM articles WHERE id = ?", (article_id,))
        if not article:
            abort(404)
        return send_from_directory(Path(article["project_path"]) / "assets", filename)

    @app.route("/articles/<int:article_id>/css/<path:filename>")
    @login_required
    def serve_article_css(article_id, filename):
        article = db.query_one("SELECT project_path FROM articles WHERE id = ?", (article_id,))
        if not article:
            abort(404)
        return send_from_directory(Path(article["project_path"]), filename)

    @app.route("/healthz")
    def healthz():
        return {"ok": True}


def _peek_title(md_path: Path) -> Optional[str]:
    if not md_path.exists():
        return None
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _serve_artifact(article_id: int, name: str):
    article = db.query_one("SELECT project_path FROM articles WHERE id = ?", (article_id,))
    if not article:
        abort(404)
    apath = Path(article["project_path"])
    target = apath / name
    if not target.exists():
        abort(404)
    return send_from_directory(apath, name)


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="127.0.0.1", port=port, debug=True)
