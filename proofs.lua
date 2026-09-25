-- Quarto parses native .proof divs into Proof nodes before user filters run.
-- Keep source semantics; display proofs as closed sibling disclosures in HTML.
function Proof(el)
  if quarto.doc.is_format("html") then
    return quarto.Callout({
      type = "tip",
      title = "Proof",
      collapse = true,
      icon = false,
      content = el.div.content,
      attr = pandoc.Attr(el.identifier)
    })
  end
end
