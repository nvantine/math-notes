local metadata = nil

local function has_class(element, class_name)
  for _, class in ipairs(element.classes) do
    if class == class_name then
      return true
    end
  end
  return false
end

local function project_path(relative_path)
  if quarto.project and quarto.project.directory then
    return quarto.project.directory .. "/" .. relative_path
  end
  return relative_path
end

local function read_file(path)
  local file, open_error = io.open(path, "r")
  if not file then
    error("math-notes-toggle: cannot open " .. path .. ": " .. tostring(open_error))
  end
  local content = file:read("*a")
  file:close()
  return content
end

local function load_metadata()
  if metadata == nil then
    local path = project_path("lean/generated/items.json")
    metadata = quarto.json.decode(read_file(path))
  end
  return metadata
end

local function tab_navigation(lean_id)
  local notes_tab = lean_id .. "-notes-tab"
  local notes_panel = lean_id .. "-notes-panel"
  local lean_tab = lean_id .. "-lean-tab"
  local lean_panel = lean_id .. "-lean-panel"

  return string.format([[
<ul class="nav nav-tabs" role="tablist">
  <li class="nav-item" role="presentation">
    <button class="nav-link active" id="%s" data-bs-toggle="tab" data-bs-target="#%s" type="button" role="tab" aria-controls="%s" aria-selected="true">Notes</button>
  </li>
  <li class="nav-item" role="presentation">
    <button class="nav-link" id="%s" data-bs-toggle="tab" data-bs-target="#%s" type="button" role="tab" aria-controls="%s" aria-selected="false">Lean 4</button>
  </li>
</ul>
]], notes_tab, notes_panel, notes_panel, lean_tab, lean_panel, lean_panel)
end

local function lean_toggle(div)
  if not has_class(div, "lean-paired") then
    return nil
  end

  local lean_id = div.attributes["lean-id"] or div.identifier
  if not string.match(lean_id, "^[a-z][a-z0-9%-]*$") then
    error("math-notes-toggle: lean-id must be lowercase kebab-case: " .. lean_id)
  end

  local item = load_metadata()[lean_id]
  if item == nil then
    error("math-notes-toggle: no generated Lean item for " .. lean_id)
  end

  local snippet = read_file(project_path(item.snippet))
  local code = pandoc.CodeBlock(
    snippet,
    pandoc.Attr(
      "",
      { "sourceCode", "lean" },
      {
        { "filename", item.source_file },
        { "code-copy", "false" },
      }
    )
  )
  local source_link = pandoc.Link(
    { pandoc.Str("View exact source on GitHub") },
    item.source_url,
    "",
    pandoc.Attr("", { "lean-source-link" })
  )

  local notes_tab = lean_id .. "-notes-tab"
  local notes_panel_id = lean_id .. "-notes-panel"
  local lean_tab = lean_id .. "-lean-tab"
  local lean_panel_id = lean_id .. "-lean-panel"

  local notes_panel = pandoc.Div(
    div.content,
    pandoc.Attr(
      notes_panel_id,
      { "tab-pane", "fade", "show", "active" },
      {
        { "role", "tabpanel" },
        { "aria-labelledby", notes_tab },
        { "tabindex", "0" },
      }
    )
  )
  local code_container = pandoc.Div(
    { code },
    pandoc.Attr("", { "lean-code" })
  )
  local lean_panel = pandoc.Div(
    { code_container, pandoc.Para({ source_link }) },
    pandoc.Attr(
      lean_panel_id,
      { "tab-pane", "fade" },
      {
        { "role", "tabpanel" },
        { "aria-labelledby", lean_tab },
        { "tabindex", "0" },
      }
    )
  )
  local tab_content = pandoc.Div(
    { notes_panel, lean_panel },
    pandoc.Attr("", { "tab-content" })
  )
  local component = pandoc.Div(
    { pandoc.RawBlock("html", tab_navigation(lean_id)), tab_content },
    pandoc.Attr("", { "math-notes-tabset" })
  )

  div.content = { component }
  return div
end

return {
  { Div = lean_toggle }
}
