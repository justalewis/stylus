// LiCS Pandoc Typst template.
//
// Variables (`$name$`) are substituted by Pandoc using the article's YAML
// front matter. The result is a `.typ` source file that Typst compiles
// to a tagged PDF.

#set document(
  $if(title)$title: "$title$",$endif$
  $if(author)$author: ($for(author)$"$it.name$"$sep$, $endfor$),$endif$
  $if(keywords)$keywords: ($for(keywords)$"$keywords$"$sep$, $endfor$),$endif$
)

#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1.25in, right: 1.25in),
  header: context {
    let p = counter(page).at(here()).first()
    if p == 1 {
      []
    } else if calc.even(p) {
      align(left, text(size: 9pt, style: "italic", "$short-authors$"))
    } else {
      align(right, text(size: 9pt, style: "italic", "$short-title$"))
    }
  },
  footer: context align(center, text(size: 9pt, str(counter(page).at(here()).first()))),
)

#set text(font: ("EB Garamond", "Cormorant Garamond", "Georgia"), size: 11pt, lang: "en")
#set par(justify: true, leading: 0.65em, first-line-indent: 1.5em)

#show heading.where(level: 1): it => {
  set text(size: 16pt, weight: "bold")
  set par(first-line-indent: 0em)
  v(1.2em)
  it.body
  v(0.4em)
}
#show heading.where(level: 2): it => {
  set text(size: 13pt, weight: "bold", style: "italic")
  set par(first-line-indent: 0em)
  v(0.8em)
  it.body
  v(0.2em)
}
#show heading.where(level: 3): it => {
  set text(size: 11pt, weight: "bold")
  set par(first-line-indent: 0em)
  v(0.5em)
  it.body
}

// Title block
align(center, {
  set par(first-line-indent: 0em)
  text(size: 18pt, weight: "bold", "$title$")
  $if(subtitle)$
  v(0.4em)
  text(size: 13pt, style: "italic", "$subtitle$")
  $endif$
  v(0.8em)
  $if(author)$
  text(size: 11pt, style: "italic", $for(author)$"$author.name$$if(author.affiliation)$ ($author.affiliation$)$endif$"$sep$ + ", " + $endfor$)
  $endif$
  v(1.2em)
})

$if(abstract)$
block(
  inset: (left: 1em, right: 1em, top: 0.5em, bottom: 0.5em),
  stroke: (top: 0.5pt, bottom: 0.5pt),
  width: 100%,
  [
    #set par(first-line-indent: 0em)
    #text(size: 10pt, weight: "bold", "Abstract")
    #v(0.3em)
    #text(size: 10pt, [$abstract$])
  ],
)
v(0.8em)
$endif$

$body$
