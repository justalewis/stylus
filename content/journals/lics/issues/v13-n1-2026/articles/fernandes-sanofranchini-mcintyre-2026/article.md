---
title: Sample Article Title
author:
- name: First Author
  affiliation: Some University
- name: Second Author
  affiliation: Another University
abstract: |
  Abstract goes here. The cleanup pipeline extracts this from the journal-submission preamble (the lines before the first `# Heading`) and emits it as a YAML block. The structured form makes the abstract visible to indexers and screen readers; it also surfaces in the deposit XML.
keywords:
- example keyword
- structured metadata
- accessible publishing
short-title: Sample Article
short-authors: First & Second Author
status: draft
section: ARTICLES
---

# Introduction

This is placeholder body content. The repository ships with one sample article record so a new user can see how the data model works end to end — metadata in YAML front matter, body in Markdown below the closing `---` fence.

The original article that lived here during development (a real submission to *Literacy in Composition Studies*) was redacted before this repository was made public so that authors' work is not redistributed without consent. Replace this placeholder with your own content when you upload your first DOCX.

See @fig:placeholder for what an inline figure reference looks like in the figure-numbering pipeline.

![A placeholder figure caption. The cleanup pipeline numbers figures automatically; this caption renders as "Figure 1: A placeholder figure caption."](assets/placeholder.svg){#fig:placeholder width=60%}

## Section heading

Section headings (level 2) render in italic, left-aligned in the article body. Level-3 headings are smaller and use a muted color.

### Sub-section heading

Body paragraphs are justified with a 1.4em first-line indent (except the first paragraph after a heading, which has no indent). Hyphenation is disabled so long words flow to the end of the line; some lines may have wider word spacing as a consequence.

> Block quotes render with a subtle left margin in the body color, smaller font size, and no border (unlike many CSS frameworks). They are appropriate for indented quotations of any length.

# Works Cited

Author Name. *Book Title*. Publisher, Year.

Other Author. "Article Title." *Journal Name*, vol. X, no. Y, Year, pp. 1–10.
