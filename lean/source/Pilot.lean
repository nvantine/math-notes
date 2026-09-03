import Mathlib

namespace MathNotes

-- MATH_NOTES_BEGIN def-relation
/-- A relation from `α` to `β` is a proposition-valued function of two arguments. -/
abbrev Relation (α β : Type*) := α → β → Prop
-- MATH_NOTES_END def-relation

-- MATH_NOTES_BEGIN exr-de-morgan-union
/-- The complement of a union is the intersection of the complements. -/
theorem compl_iUnion {α ι : Type*} (A : ι → Set α) :
    (⋃ i, A i)ᶜ = ⋂ i, (A i)ᶜ := by
  ext x
  simp
-- MATH_NOTES_END exr-de-morgan-union

-- MATH_NOTES_BEGIN exr-double-negation
/-- Taking the additive inverse twice returns the original element. -/
theorem neg_neg_element {V : Type*} [AddGroup V] (v : V) : -(-v) = v := by
  exact neg_neg v
-- MATH_NOTES_END exr-double-negation

end MathNotes
