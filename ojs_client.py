"""Lightweight OJS REST API client for galley submission.

OJS 3.3+ exposes a REST API (`/api/v1/...`). This client posts a
rendered galley package to an OJS submission. Requires:
  - the OJS site URL (with /index.php/<journal_slug>/api/v1)
  - an API token (generated in the user's OJS profile)
  - the submission id (created in OJS UI; Graphion attaches galley to it)

The token and URL live in journal settings (or env vars) since they're
per-journal. This client only handles galley upload; the submission
itself must already exist in OJS.

Note: OJS's REST API surface is still evolving; specific endpoints can
shift between versions. This is a thin wrapper that aims to be obvious
to patch when needed.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


def _requests():
    """Defer the requests import so the module loads without it (we
    technically have it as a hard dep, but be defensive)."""
    import requests
    return requests


def _config_from_journal(journal: Dict) -> Dict[str, Optional[str]]:
    """Pull OJS config from a journal row. Env vars override DB fields,
    so per-deployment overrides are easy.
    """
    return {
        "url": os.environ.get("OJS_URL") or journal.get("ojs_url"),
        "token": os.environ.get("OJS_API_TOKEN") or journal.get("ojs_api_token"),
        "context_id": (
            os.environ.get("OJS_CONTEXT_ID")
            or str(journal.get("ojs_context_id") or "")
        ),
    }


def ojs_configured(journal: Dict) -> bool:
    cfg = _config_from_journal(journal)
    return bool(cfg["url"] and cfg["token"])


def upload_galley(
    journal: Dict,
    submission_id: int,
    galley_label: str,
    galley_locale: str,
    file_path: Path,
) -> Dict:
    """Upload a galley file to an existing OJS submission.

    Returns the OJS response body (parsed JSON) on success. Raises
    Exception with the OJS error message on failure.

    `galley_label`: free text shown in OJS, e.g., "HTML" or "PDF".
    `galley_locale`: BCP-47 code, e.g., "en_US" or "en".
    `file_path`: local path to the file to upload (HTML, PDF, EPUB,
        ZIP — OJS accepts whatever you send).
    """
    cfg = _config_from_journal(journal)
    if not cfg["url"] or not cfg["token"]:
        raise RuntimeError(
            "OJS is not configured for this journal. Set OJS_URL and "
            "OJS_API_TOKEN env vars, or fill the OJS fields in Journal "
            "Settings."
        )
    requests = _requests()
    base = cfg["url"].rstrip("/")
    headers = {"Authorization": f"Bearer {cfg['token']}"}

    # Step 1: upload the file to OJS's temporary file store. The API
    # returns a temporaryFileId we then bind to a galley.
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        r = requests.post(
            f"{base}/_uploadPublicFile", headers=headers, files=files, timeout=120,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"OJS file upload failed: {r.status_code} {r.text[:300]}")
    upload_resp = r.json()
    temp_id = upload_resp.get("temporaryFileId") or upload_resp.get("id")
    if not temp_id:
        raise RuntimeError(f"OJS upload returned no temporaryFileId: {upload_resp}")

    # Step 2: create the galley + attach the file.
    payload = {
        "label": galley_label,
        "locale": galley_locale,
        "temporaryFileId": temp_id,
        "submissionFileType": "submissionGalley",
    }
    r = requests.post(
        f"{base}/submissions/{submission_id}/galleys",
        headers=headers, json=payload, timeout=120,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"OJS galley create failed: {r.status_code} {r.text[:300]}")
    return r.json()


def list_submissions(journal: Dict) -> list:
    """Return a list of submissions on the configured OJS journal,
    each with id + title. For populating a "pick submission" dropdown.
    """
    cfg = _config_from_journal(journal)
    if not cfg["url"] or not cfg["token"]:
        return []
    requests = _requests()
    base = cfg["url"].rstrip("/")
    headers = {"Authorization": f"Bearer {cfg['token']}"}
    r = requests.get(f"{base}/submissions", headers=headers, timeout=30)
    if r.status_code >= 400:
        return []
    body = r.json()
    items = body.get("items", []) if isinstance(body, dict) else body
    out = []
    for s in items:
        title = ""
        if isinstance(s.get("publications"), list) and s["publications"]:
            pub = s["publications"][0]
            title_obj = pub.get("fullTitle", {}) or pub.get("title", {})
            if isinstance(title_obj, dict):
                title = next(iter(title_obj.values()), "") if title_obj else ""
            else:
                title = str(title_obj)
        out.append({"id": s.get("id"), "title": title or f"Submission {s.get('id')}"})
    return out


__all__ = [
    "ojs_configured",
    "upload_galley",
    "list_submissions",
]
