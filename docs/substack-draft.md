# Stylus, or: How I Stopped Worrying and Built a Publishing Pipeline for Rhet/Comp

I've spent the last several years doing layout for *Literacy in Composition Studies*, and the way the work goes is something like this. An author sends me a Word document. I open it in InDesign for the PDF and Dreamweaver for the HTML. I rebuild the article's typography by hand in each tool, twice, because they don't share a source. I lay out figures. I tag headings. I cross-check the table of contents against the actual articles. I export. I upload to OJS. I move on to the next article. For an issue with five or six articles I'm spending three full days, not because the work is hard but because the work is duplicate.

About six weeks ago I started building an alternative. The result is called **[Stylus](https://github.com/justalewis/stylus)**, and it's now public under GPL-3.0. It is a single-editor publishing workstation: you upload a Word document, you correct what needs correcting in a form-based UI (no Markdown required, though it's there for power users), you click Render, and you get a publication-grade semantic HTML galley, a tagged 6×9 book-trim PDF, an EPUB, a JATS XML for indexers, and a CrossRef deposit XML for DOI registration. All from one canonical Markdown source.

I want to write about two things this tool changes for our field. One is about accessibility. The other is about the infrastructure of scholarly indexing — what makes our work findable, citable, and durable. I think both matter, and I think rhet/comp as a field has been quietly losing ground on both for years.

## The accessibility problem

Open a recent issue of almost any rhet/comp journal that hosts its content as PDF. Try to read it with a screen reader. What happens depends on how the PDF was produced. If it was exported from InDesign with tagging enabled and the tags were curated, you get a navigable document — the reader can jump between headings, blockquotes get announced as such, figure alt text reads aloud. If it was exported with default settings, you get a flat document that the screen reader speaks linearly with no structural cues, or worse, in the wrong reading order if the InDesign frames were arranged the way layout people arrange frames.

Most rhet/comp PDFs in my experience are the second kind. Not because layout editors don't care about accessibility — most do — but because curating tags in InDesign is a tedious, error-prone, easy-to-skip step that has to happen by hand for every issue. Layout editors who have any other deadline pressure (and they all do) skip it.

HTML galleys are sometimes better and sometimes worse. OJS produces decent galley HTML when the source is structured cleanly. When the source is a journalist-style Word document with manual line breaks and inconsistent heading styles, OJS's galley generator can't recover the structure that wasn't there. The galley is then a flat sea of paragraphs with no `<section>` boundaries, no `<aside>` for the abstract, no proper heading hierarchy, no `aria-label` for keywords or works cited. A screen reader user can read the text but can't navigate it.

Stylus changes the production economics for both problems. Because the canonical source is Markdown — structured, semantic, lossless — every output format preserves structure by construction. The HTML it produces uses `<article>`, `<section class="level1">`, `<aside class="keywords" aria-label="Keywords">`, `<section class="abstract" aria-label="Abstract">`, `<section id="works-cited" class="references">`. The PDF is tagged automatically by Typst (Pandoc and InDesign both struggle with this in different ways; Typst handles it as a first-class feature). Alt text on figures is a lint check, not an afterthought; the lint pass flags missing alt text before deposit. Heading hierarchy is preserved through the Pandoc pipeline. Hanging indent on Works Cited is a CSS class, not a tab-stop kluge. Hyphenation is disabled by default so long words don't get mangled.

None of this is novel — these are basic web standards and basic PDF/UA practices. What's novel is that Stylus does them by default, with no manual tagging step, because the source format makes structure visible to the rendering pipeline. The only way to produce an untagged PDF is to deliberately break the toolchain.

There's a longer version of this argument that I won't make here, but briefly: rhet/comp has spent twenty years writing about literacy as situated, embodied, and accessible without consistently making our own content accessible to readers who depend on assistive tech. That's a gap I'd like to help close. Tooling that makes accessibility the path of least resistance is one piece of how I think it can happen.

## The scholarly infrastructure problem

The second thing Stylus is trying to do is harder to see if you don't think much about the systems that make scholarship findable. So a brief tour.

When you publish an article and want it to be cited, indexed, and linked to other scholarship, you participate in a small constellation of standards-driven services. CrossRef issues your article a DOI, which is a permanent identifier the article gets to keep even if your journal's URL structure changes. PubMed Central indexes the full text of articles in its scope using a markup language called JATS (Journal Article Tag Suite). DOAJ lists the journal in its directory using a different but related markup. Reference linkers — the bits of metadata in `<a href="https://doi.org/...">` — let readers click from a citation in your bibliography to the work being cited. ORCIDs (the per-author identifiers we've all been registering since 2015) flow through these systems to disambiguate "S. Jones" the historian from "S. Jones" the literacy scholar.

The catch: most of this infrastructure works only if you deposit *structured* metadata with the right schemas. CrossRef accepts deposit XML in their 5.3.1 schema. PMC accepts JATS in their archiving tag set. Reference linking works only if the bibliography is emitted with structured `<element-citation>` elements containing the cited work's title, authors, journal, year, DOI as separate fields, not as a single prose blob. ORCID propagation works only if the deposit XML carries ORCIDs as `<contrib-id contrib-id-type="orcid">` elements.

If you do these deposits by hand — which is what most small humanities journals do, when they do them at all — you do them sparingly, with whatever shortcuts make the deposit pass schema validation. Hand-crafted CrossRef deposits typically use `<unstructured_citation>` elements for references, which means CrossRef accepts the deposit but the reference linking graph never picks up the cited works. ORCID often doesn't make the trip. JATS for PMC is the kind of thing only the best-resourced journals attempt at all.

Stylus produces all of this from the same canonical Markdown source the editor was already working with. If the article has a `references.bib` file (which the author probably has anyway from Zotero or another reference manager), the CrossRef deposit gets structured `<journal_title>`, `<author>`, `<volume>`, `<first_page>`, `<cYear>`, `<article_title>`, `<doi>` elements per citation, and the JATS gets the equivalent `<element-citation>` with `<person-group>`, `<source>`, `<fpage>`, `<lpage>`, `<pub-id>`. ORCIDs in the metadata form propagate to both CrossRef contributors and JATS contrib elements. The DOI auto-assigns from the journal's configured pattern. The deposit XML is downloadable as a button-click; the editor uploads it to CrossRef admin with no further hand-editing.

The same thing happens for JATS. You get a JATS-archiving-1.3 conformant XML with `<journal-meta>`, `<article-meta>` containing DOI / title / contributors / pub-date / volume / issue / fpage / lpage / abstract / kwd-group, a Pandoc-rendered `<body>`, and a structured `<ref-list>` in the back. Suitable for PMC submission, suitable for DOAJ, suitable for any indexer that consumes JATS.

I don't think most rhet/comp journals will start depositing to PMC tomorrow. PMC is selective, and not all rhet/comp content fits its scope. But every other indexer — DOAJ, Scopus, EBSCO, ProQuest, Google Scholar's structured-data crawlers — benefits from JATS. The more of our content lives as well-formed JATS, the more discoverable our field becomes to readers who didn't already know where to look.

## What this is, what this isn't

Stylus is one editor's tool. It's not a peer-review system, an author submission portal, or a hosted journal site. OJS does the first two well; the third is what most of our journals already have.

What Stylus replaces is the production-and-layout middle of the workflow — the part where an editor takes an accepted manuscript and turns it into the galleys and deposit metadata that get uploaded back into the public-facing system. That's where the duplicate work happens, that's where accessibility and structured-metadata commitments quietly get lost, and that's where Stylus does its best work.

The codebase is GPL-3.0. The architecture is per-journal: each journal has its own template bundle (CSS, Pandoc HTML template, Pandoc Typst template, Lua filters, citation style, wordmark image), so customizing for another journal is a matter of editing a few files in a directory, not forking the whole project. There's a CLI scaffolder (`python new_journal.py <slug> "<Name>"`) that copies the LiCS bundle as a starting point; you customize it from there.

I'd love for other journals to try it. The repository ships with extensive documentation, including a step-by-step **[Installation guide](https://github.com/justalewis/stylus/blob/main/docs/help/12-installation.md)** for getting it running locally and a **[Customization guide](https://github.com/justalewis/stylus/blob/main/docs/help/13-customization.md)** that walks through how to adapt the LiCS-flavored defaults to a different journal's brand. The in-app `/help` section surfaces all of this from a sidebar while you're working — both lay-reader explanations and technical depth for editors who want to know how the pipeline actually works.

## What's next

What I'd most like to see Stylus do is make the things I described above feel **normal**. Right now, tagged PDFs and JATS deposits are things humanities journals occasionally aspire to and rarely produce. With a tool that makes them happen by default, the cost of *not* producing them becomes higher than the cost of producing them. That's the only way I know of to move a field's practices.

The roadmap (see [docs/audit-and-roadmap.md](https://github.com/justalewis/stylus/blob/main/docs/audit-and-roadmap.md) in the repository) tracks specific feature work: a citation linter that's stricter than the heuristic version that's there now; ROR identifiers for institutional affiliations and CrossRef Funder Registry for grant attribution; deposit-history tracking; an automated accessibility audit using axe-core for the HTML and verapdf for the tagged PDF. None of these are huge; all of them remove friction from doing the right thing.

If you edit a journal in rhet/comp, or in any small humanities field where the production gap I'm describing rings true, please try Stylus. Open issues at the repo with the things that don't work for your journal. I'd rather know what's missing than guess.

Repository: <https://github.com/justalewis/stylus>

---

*This post is also available as the README in the repository, alongside the in-app help documentation that walks through every step of the workflow. Built with help from Claude Code; the typography of the rendered articles approximates LiCS's print issues; the admin UI uses the [Lewis Design System](https://github.com/justalewis/lewis-design-system).*
