theorem add_inv_swap : ∀ v : V, ((0 : ℝ) • v = 0 ↔ ∃ w : V, v + w = 0) := by
  intro v
  constructor
  · intro h
    use (-1 : ℝ) • v
    nth_rewrite 1 [← one_smul ℝ v]
    rw [← add_smul]
    rw [show (1 + -1 : ℝ) = 0 from by ring]
    rw [h]
  · intro h
    exact zero_smul_eq_zero v
