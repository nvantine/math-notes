/-- Taking the additive inverse twice returns the original element. -/
theorem neg_neg_element {V : Type*} [AddGroup V] (v : V) : -(-v) = v := by
  exact neg_neg v
