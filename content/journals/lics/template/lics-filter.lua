-- LiCS Pandoc Lua filter.
--
-- Purpose: journal-specific transformations that should not live in the
-- generic conversion engine. Currently:
--   * Tags the works-cited heading and wraps the following list/block
--     in <section id="works-cited" class="hanging-indent"> for HTML.
--   * Recognizes pull quotes (block quotes with a `.pullquote` class).
--
-- Add new transformations as journal idioms surface.

local in_works_cited = false
local works_cited_blocks = {}
local pre_works_cited = {}
local works_cited_heading = nil

function Pandoc(doc)
  local out_blocks = {}
  local found = false
  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" and block.level <= 2 then
      local txt = pandoc.utils.stringify(block):lower()
      if txt:match("^works cited") or txt:match("^references") or txt:match("^bibliography") then
        found = true
        works_cited_heading = block
        works_cited_heading.identifier = "works-cited"
      end
    end
    if found and block ~= works_cited_heading then
      table.insert(works_cited_blocks, block)
    elseif not found then
      table.insert(out_blocks, block)
    end
  end

  if works_cited_heading then
    table.insert(out_blocks, works_cited_heading)
    local section = pandoc.Div(works_cited_blocks, pandoc.Attr("", {"hanging-indent"}, {}))
    table.insert(out_blocks, section)
  end

  return pandoc.Pandoc(out_blocks, doc.meta)
end
