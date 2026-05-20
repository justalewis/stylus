"""Unit tests for cleanups.py.

Each pass has at least one input/output pair, plus an idempotence check
across the full pipeline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cleanups


def _log():
    return cleanups.CleanupLog()


def test_strip_highlighter_spans():
    src = "Hello [important phrase]{.mark}, world."
    out = cleanups.strip_highlighter_spans(src, _log())
    assert out == "Hello important phrase, world."


def test_strip_highlighter_spans_idempotent():
    src = "Hello [important phrase]{.mark}, world."
    once = cleanups.strip_highlighter_spans(src, _log())
    twice = cleanups.strip_highlighter_spans(once, _log())
    assert once == twice


def test_unescape_quoted_brackets():
    src = r"As Crawford notes, \[citation needed\]."
    out = cleanups.unescape_quoted_brackets(src, _log())
    assert out == "As Crawford notes, [citation needed]."


def test_unescape_quoted_brackets_idempotent():
    src = r"\[a\] then \[b\]"
    a = cleanups.unescape_quoted_brackets(src, _log())
    b = cleanups.unescape_quoted_brackets(a, _log())
    assert a == b == "[a] then [b]"


def test_reassemble_heading_linebreaks_pipe():
    src = "# First half \\|Second half\n\nBody text."
    out = cleanups.reassemble_heading_linebreaks(src, _log())
    assert out.startswith("# First half Second half")


def test_reassemble_heading_linebreaks_no_change():
    src = "# Normal heading\n\nBody."
    out = cleanups.reassemble_heading_linebreaks(src, _log())
    assert out == src


def test_strip_orphan_page_numbers_at_end():
    src = "Some content.\n\n\n42\n"
    out = cleanups.strip_orphan_page_numbers(src, _log())
    assert not out.rstrip().endswith("42")


def test_strip_orphan_page_numbers_mid_file_kept():
    src = "Section 1\n\n42\n\nMore content."
    out = cleanups.strip_orphan_page_numbers(src, _log())
    assert "42" in out


def test_normalize_dashes():
    src = "She said yes—then changed her mind."
    out = cleanups.normalize_dashes(src, _log())
    assert out == "She said yes---then changed her mind."


def test_normalize_dashes_idempotent():
    src = "yes—no"
    a = cleanups.normalize_dashes(src, _log())
    b = cleanups.normalize_dashes(a, _log())
    assert a == b


def test_build_yaml_front_matter_basic_lics():
    src = (
        "An Article About Citation\n"
        "Jane Crawford—Penn State\n"
        "John Hao—UC Irvine\n"
        "Keywords\n"
        "citation; ethics; pedagogy\n"
        "Abstract\n"
        "This essay examines citational practices.\n"
        "\n"
        "# Introduction\n"
        "\n"
        "Opening paragraph.\n"
    )
    out = cleanups.build_yaml_front_matter(src, _log())
    assert out.startswith("---\n")
    assert "title: An Article About Citation" in out
    assert "Jane Crawford" in out
    assert "Penn State" in out
    assert "ethics" in out
    assert "# Introduction" in out


def test_build_yaml_front_matter_idempotent():
    src = (
        "An Article\n"
        "Jane—Penn State\n"
        "Abstract\n"
        "Body of abstract.\n"
        "\n"
        "# Intro\n\n"
        "Body.\n"
    )
    once = cleanups.build_yaml_front_matter(src, _log())
    twice = cleanups.build_yaml_front_matter(once, _log())
    assert once == twice


def test_run_all_idempotent():
    src = (
        "An Article About Citation\n"
        "Jane Crawford—Penn State\n"
        "Keywords\n"
        "citation; ethics\n"
        "Abstract\n"
        "Examines [important]{.mark} citational practices.\n"
        "\n"
        "# Introduction\\|Subhead\n"
        "\n"
        "Opening with \\[brackets\\] and a dash—right here.\n"
        "\n"
        "42\n"
    )
    once, _ = cleanups.run_all(src)
    twice, _ = cleanups.run_all(once)
    assert once == twice


def test_run_all_strips_highlight_and_dash_in_body():
    src = (
        "A Title\n"
        "Jane—UC\n"
        "Abstract\n"
        "Short.\n"
        "\n"
        "# Body\n"
        "Yes—indeed [foo]{.mark} bar.\n"
    )
    out, _ = cleanups.run_all(src)
    assert "{.mark}" not in out
    assert "—" not in out
    assert "foo bar" in out
    assert "yes---indeed" in out.lower()


def test_author_affiliation_em_dash():
    src = (
        "A Title\n"
        "Jane Crawford—Penn State University\n"
        "Abstract\n"
        "Short.\n"
        "\n"
        "# Body\n"
        "Body text.\n"
    )
    out, _ = cleanups.run_all(src)
    assert "name: Jane Crawford" in out
    assert "affiliation: Penn State University" in out


def test_author_with_hyphenated_name():
    """Author 'Sano-Franchini' should not be split at the hyphen."""
    src = (
        "A Title\n"
        "Jenny Sano-Franchini—Virginia Tech\n"
        "Abstract\n"
        "Short.\n"
        "\n"
        "# Body\n"
        "Body text.\n"
    )
    out, _ = cleanups.run_all(src)
    assert "name: Jenny Sano-Franchini" in out
    assert "affiliation: Virginia Tech" in out
