**LiCS Editorial Style Guide**

This file is the canonical editorial style for *Literacy in Composition Studies*. It is read by Graphion's "Stylize article (Claude)" button — Claude reads this guide and applies it to article manuscripts. Edit this file to change house style across all future stylize runs.

**Important to Claude**: preserve the author's content verbatim. Restructure formatting only. Never paraphrase, summarize, or invent. If something is ambiguous, prefer the convention in this guide over making up new structure.

**Heading hierarchy**

-   Section headings: \#\# H2 (e.g., \#\# Introduction, \#\# Conclusion)
-   Subsection headings: \#\#\# H3
-   Sub-subsections: \#\#\#\# H4 (rarely needed)
-   Do not use H1 for body sections — that level is reserved for the title (which lives in the YAML front matter, handled separately)
-   Works Cited heading is \#\#\# Works Cited (H3 level — matches LiCS print convention)
-   Notes / Endnotes heading is \#\#\# Notes
-   Add a blank line above and below every heading

**Paragraph structure**

-   One blank line between paragraphs
-   Drop cap on the first paragraph is automatic — no markup needed
-   No double-blank-lines (collapse to single)
-   Body paragraphs use first-line indent (handled by template — no leading spaces in source)

**Works Cited**

This is the most important section to fix because Word-style manuscripts commonly mangle it.

-   Each entry is its own paragraph, separated by a blank line
-   If you see entries running together (publisher of one entry followed by a comma and the surname of the next — e.g., \*Book.\* U of Illinois P, Smith, Jane. ...), SPLIT them into separate paragraphs and replace the comma with the closing punctuation of the first entry (period, or comma+year if year is known to be missing)
-   MLA 9 format (8th-ed updated)
-   Italicize book and journal titles with \*...\*
-   Article titles in straight "..." quotes (the template handles smart-quote rendering)
-   Page ranges with en-dash: pp. 1–21 (use Unicode – or –, not double-hyphen)
-   DOIs as bare URLs in angle brackets: \<https://doi.org/10.21623/1.7.1.2\>
-   Each entry should be **detectable as a single sentence/period-terminated chunk** — that's how Pandoc splits paragraphs

**Tables**

-   **Single-cell "rectangle" tables** (Word text boxes / callout boxes): convert to blockquote (\> content...) — the template renders these as indented italic callouts
-   **Multi-cell data tables**: keep as Markdown tables. Prefer pipe tables (\| col \| col \|\\n\|---\|---\|) for simple data; use grid tables (+---+---+) only when cells need multiple paragraphs
-   Strip any Microsoft Office HTML cruft (\<span style="mso-..."\>) from cell content
-   Preserve column headers as the first row with a separator line below
-   Tables with 4+ columns are auto-rendered in landscape orientation by the template — no source markup needed
-   Tables with 2-3 columns are auto-shrunk to 8pt — no source markup needed

**Block quotes**

-   Lines beginning with \> for the entire quote
-   Do not include surrounding quotation marks; the block quote treatment IS the marker
-   Multi-paragraph block quotes: blank line within, with each new paragraph also prefixed \>
-   Block quote citation goes at the end of the last line: \> ... last sentence. (Author 42)

**Inline formatting**

-   *Italics* (\*...\*) for book and journal titles, foreign words, emphasis, named theoretical concepts
-   **Bold** (\*\*...\*\*) for section labels or key terms that aren't headings
-   "Curly quotes" — the template converts straight "..." to curly automatically
-   Use – (en-dash) for numerical ranges (pages, years): 1–21, 2019–2024
-   Use — (em-dash) for parenthetical breaks: the practice — radical, queer, ongoing — continues
-   Use … (Unicode ellipsis) instead of three dots ...
-   Apostrophes: curly ' not straight ' (template converts)

**In-text citations**

-   MLA author-page format: (Smith 42), (Lu and Horner 587)
-   Multiple sources: (Smith 42; Jones 87) — semicolon-separated
-   Block quote citation: (Author Page) AFTER the closing period, on its own line if convenient
-   Quoted phrases with attribution: "the practice continues" (Smith 42)

**Footnotes and endnotes**

-   Use Pandoc footnote syntax: [\^1] inline, [\^1]: for the definition
-   Each [\^N]: definition is its own paragraph (blank line before each)
-   Convert Pandoc Div-style footnotes (::: {\#footnote-N} ... :::) to canonical [\^N]: form
-   Footnote definitions go at the end of the article (Pandoc auto-renders them as endnotes; the LiCS template emits them as a "Notes" section)

**What to fix (common problems)**

-   **Run-on Works Cited entries**: split into one entry per paragraph
-   **Broken tables**: collapsed onto one line, with blank lines between rows → repair to consecutive rows
-   **Word HTML cruft**: any \<span lang="..." style="mso-..."\> survival should be stripped
-   **Stray pipe characters** in cell content (escaped \\\| or literal \|) → remove
-   **Smart quote inconsistency**: normalize toward Unicode curly quotes
-   **Doubled spaces**: collapse to single
-   **Pandoc auto-generated heading IDs** ({\#section style="text-align: center;"}): drop the inline attributes; let Pandoc auto-generate clean IDs
-   **Stray [?](\#footnote-ref-N) back-arrows**: these are Pandoc HTML round-trip artifacts; remove them (Pandoc native footnotes generate back-arrows automatically)

**What to preserve**

-   All citations, including parenthetical and block-quote attributions
-   All URLs and DOIs, exactly as given
-   Author voice and word choice — never paraphrase
-   Existing footnote markers and their content
-   Block quote contents verbatim (only fix the markup around them)
-   Image references (![alt](path)) exactly as written

**Pull-quotes**

Articles sometimes feature pull-quotes: short, visually prominent excerpts from the body text, displayed as marginal or inset callouts. In LiCS print issues these typically appear as large italic text in quotation marks, set apart from the running prose.

-   Mark pull-quotes with a Pandoc fenced div: ::: pullquote on its own line, the quoted text on the next line(s), then ::: on its own line to close
-   Pull-quote content is **a verbatim repetition of text already in the body** — it is a display callout, not new content. Do not invent pull-quote text and do not paraphrase
-   Place the ::: pullquote ... ::: block in the source roughly where it should appear visually (near the body sentence it duplicates), even though the template may float it
-   Do not include surrounding quotation marks in the source; the template adds the curly-quote treatment
-   Leave a blank line before and after the fenced div

Example:

Stillness is a major part of preferred gestural listening in schools, yet it too battles negative connotations of passiveness.

::: pullquote

Stillness is a major part of preferred gestural listening in schools, yet it too battles negative connotations of passiveness.

:::

In Watkins's writing about the development of scholarly "dispositions"…

**Genre: Editors' Introduction**

The Editors' Introduction opens each issue and previews the pieces inside. It runs as continuous prose without internal headings.

-   **No section headings.** The intro flows as one continuous sequence of paragraphs from opening to sign-off
-   **No Works Cited, no Notes section** — the intro does not cite externally in the formal sense; it references the issue's own pieces by author name and article title
-   **Article titles referenced inside the intro**: use straight "..." quotes around the article title (the template renders curly), and italicize special-issue titles or book titles with \*...\*
-   **Author names** on first reference: full name, sometimes with tribal or institutional affiliation in parentheses (e.g., Jason Hockaday (Karuk)). Preserve exactly as the editors wrote them
-   **Page citations to pieces in the same issue**: parenthetical (48) or (50) format, same as regular MLA — these refer to pages of the in-issue article being previewed
-   **Sign-off**: the final paragraph is the list of editor names, on its own line(s), prefixed with an em-dash — and italicized. Format as a single italicized line (or wrapped lines) starting with —. Example:

—\*Alanna Frost, Brenda Glascott, Al Harahap, Brian Hendickson, Tara Lockhart, Juli Parrish, Katie Silvester, Lisa Termain, and Chris Warnick\*

-   The sign-off is the LAST line of the document. Nothing follows it
-   No drop cap markup needed — the first paragraph gets one automatically, same as all other genres

**Genre: Article**

Full-length scholarly articles are the journal's primary genre. They follow the conventions above with these additions:

-   **Keywords block**: immediately after the title (which lives in YAML front matter), the article begins with a keywords line. Format as a paragraph starting with \*\*KEYWORDS\*\* on its own line, followed by a single line of semicolon-separated terms in lowercase. Example:

\*\*KEYWORDS\*\*

listening; gesture; literacy; embodiment; neurodivergence; pedagogy

-   **Section headings**: use \#\# H2 as documented above. The template renders these in centered small-caps display style; do NOT write them in ALL CAPS in source — use normal title case and let the template style them (e.g., \#\# A Litany for Gestural Listening, not \#\# A LITANY FOR GESTURAL LISTENING)
-   **Subsection headings**: \#\#\# H3, rarely needed
-   **Italicized inline "leads"**: some articles use an italicized phrase or sentence at the start of a paragraph as a rhetorical lead-in (e.g., Feibush's litany petitions: *Gestural listening captures listening's dual material and metaphorical qualities.*). These are inline italics, NOT headings — keep them as \*...\* emphasis within the paragraph, with the paragraph continuing in roman immediately after
-   **Pull-quotes**: see the Pull-quotes section above
-   **Block quote scene-setting**: articles sometimes open a section with an italicized narrative scene (e.g., a film description) set as a block quote. Mark as a standard \> block quote, with the entire scene italicized via \*...\* inside the block quote. The template renders this as indented italic
-   **Notes section**: numbered footnotes using [\^1] syntax, definitions at end of document. The template auto-titles the rendered section "NOTES"
-   **Works Cited**: standard \#\#\# Works Cited heading at the very end of the document (after Notes, if present), one entry per paragraph, MLA 9 format
-   **Anonymized student sources**: when an article cites student writing under a pseudonym, the Works Cited entry uses the pseudonym in brackets after Anonymous student A, e.g., Anonymous student A (Dylan). "The Spazzy Kid." — preserve exactly as the author wrote it

**Genre: Book Review**

Book reviews are shorter than articles, usually unstructured by internal headings, and follow a recognizable opening-personal-anecdote → book-summary → assessment arc.

-   **Title structure** is three-part and lives in YAML front matter, not the body — the body begins with the opening prose. The three parts are:
    1.  The reviewer's essay-style title (e.g., "All Are Connected: From Traditional Chinese Medicine to Students' Literacy Practices")
    2.  A Review of \*Book Title\* by Author Name line
    3.  Reviewer name and affiliation
-   **No internal section headings.** Book reviews run as continuous prose from opening to close. Do not insert \#\# H2 headings; if the YAML/template adds title block elements, those are handled separately
-   **Drop cap** on the first body paragraph is automatic, as in all genres
-   **Foreign-language characters and non-Latin scripts** (e.g., Chinese 博大精深, Japanese kana, Arabic, etc.): preserve as Unicode in the source exactly as the reviewer wrote them. Do NOT italicize them — the template handles font fallback. Italicize a transliteration or gloss if the reviewer provides one (e.g., \*pinyin\*), but not the original-script characters themselves
-   **In-text page citations to the book under review**: bare (23), (166), etc. — no author name needed since the book is the implicit referent. Citations to OTHER works use standard MLA (Author Page)
-   **Works Cited**: standard \#\#\# Works Cited heading at the end. The book under review is itself one of the entries
-   **No Notes section** is typical, though footnotes are permitted if the reviewer used them — handle with the same [\^N] syntax as articles

**Output format**

Return ONLY the rewritten Markdown body. No YAML front matter (it's stripped before this prompt and re-attached after). No code fences. No "Here is the rewritten article" preamble. No closing remarks. Just the Markdown.
