"""Bundled citation styles.

The `csl/` directory at the repo root ships a handful of common CSL
files. The Journal Settings UI exposes them via a dropdown; saving a
selection copies the chosen .csl into the journal's template directory
(replacing any prior CSL there).

To add a style: drop the .csl into `csl/` and add an entry below.
To use a style not bundled here: place the file in the journal's
template directory and leave the journal's citation_style field empty
(the renderer picks up whatever .csl it finds via _citation_args).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import config


# (key, display name) — order is the dropdown order
BUNDLED_STYLES: list[tuple[str, str]] = [
    ("mla-9", "MLA 9"),
    ("apa-7", "APA 7"),
    ("chicago-author-date", "Chicago 17 (author-date)"),
    ("chicago-notes-bibliography", "Chicago 17 (notes-bibliography)"),
    ("ieee", "IEEE"),
]

BUNDLED_KEYS = {k for k, _ in BUNDLED_STYLES}

CSL_DIR = config.BASE_DIR / "csl"


def install_style(template_dir: Path, style_key: str) -> Path:
    """Copy the requested bundled CSL into `template_dir`, removing any
    other .csl files there first. Returns the path to the installed file.
    Raises FileNotFoundError if the style isn't bundled."""
    if style_key not in BUNDLED_KEYS:
        raise FileNotFoundError(f"Citation style {style_key!r} is not bundled.")
    src = CSL_DIR / f"{style_key}.csl"
    if not src.exists():
        raise FileNotFoundError(f"Bundled CSL file missing: {src}")
    template_dir.mkdir(parents=True, exist_ok=True)
    # Remove any existing .csl files so only one remains
    for old in template_dir.glob("*.csl"):
        old.unlink()
    dest = template_dir / src.name
    shutil.copy2(src, dest)
    return dest
