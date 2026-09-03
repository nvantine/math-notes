/-- The complement of a union is the intersection of the complements. -/
theorem compl_iUnion {α ι : Type*} (A : ι → Set α) :
    (⋃ i, A i)ᶜ = ⋂ i, (A i)ᶜ := by
  ext x
  simp
