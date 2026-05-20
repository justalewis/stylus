-- LiCS Pandoc Lua filter.
--
-- Works in tandem with `--section-divs`. Pandoc auto-wraps each H1
-- section in `<section class="level1">`; this filter adds extra classes
-- and identifiers so the article.css selectors match the design:
--
--   * First H1 section gets class "opening" (enables the drop cap in HTML
--     via section.opening > h1 + p::first-letter)
--   * Works Cited / References / Bibliography H1 gets:
--       - identifier "works-cited"
--       - class "references"
--
-- For Typst output, the filter additionally wraps the first character of
-- the first paragraph of the opening section in a #dropcap[X] raw inline.
-- This is needed because Pandoc's Typst writer does not propagate header
-- classes, so we cannot key a Typst `show` rule on the `opening` class.
-- HTML output uses CSS `::first-letter`; the drop cap there does not need
-- the wrapping.
--
-- Additional journal idioms (pull quotes, epigraphs, etc.) can be added
-- here as patterns surface.

local first_h1_seen = false

local function is_references_heading(header)
  local txt = pandoc.utils.stringify(header):lower()
  return txt:match("^works cited") ~= nil
      or txt:match("^references") ~= nil
      or txt:match("^bibliography") ~= nil
end

function Header(el)
  if el.level == 1 then
    if not first_h1_seen then
      first_h1_seen = true
      table.insert(el.classes, "opening")
    end
    if is_references_heading(el) then
      el.identifier = "works-cited"
      table.insert(el.classes, "references")
    end
    return el
  end
  return nil
end

-- Typst-only: inject a #dropcap[X] raw inline at the start of the first
-- paragraph of the opening section.
local function inject_typst_dropcap(blocks)
  local in_opening = false
  local injected = false
  for _, block in ipairs(blocks) do
    if block.t == "Header" and block.level == 1 then
      in_opening = false
      for _, cls in ipairs(block.classes or {}) do
        if cls == "opening" then in_opening = true end
      end
    elseif in_opening and not injected and block.t == "Para" then
      injected = true
      local first = block.content[1]
      -- Find the first Str inline with at least one character.
      local first_str_idx = nil
      for i, inline in ipairs(block.content) do
        if inline.t == "Str" and #inline.text > 0 then
          first_str_idx = i
          break
        end
      end
      if first_str_idx then
        local s = block.content[first_str_idx].text
        local letter = s:sub(1, 1)
        local rest = s:sub(2)
        local dropcap_raw = pandoc.RawInline("typst", "#dropcap[" .. letter .. "]")
        block.content[first_str_idx] = pandoc.Str(rest)
        table.insert(block.content, first_str_idx, dropcap_raw)
      end
    end
  end
  return blocks
end

function Pandoc(doc)
  if FORMAT == "typst" then
    doc.blocks = inject_typst_dropcap(doc.blocks)
  end
  return doc
end
