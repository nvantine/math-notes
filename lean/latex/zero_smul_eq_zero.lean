theorem zero_smul_eq_zero : ∀ v : V, (0 : ℝ) • v = 0 := by
  intro v
  have h : (0 : ℝ) • v = (0 : ℝ) • v + (0 : ℝ) • v := by
    nth_rewrite 1 [← add_zero (0 : ℝ)]
    rw [add_smul]
  have h2 : (0:ℝ) • v + -((0:ℝ) • v) = ((0:ℝ) • v + (0:ℝ) • v) + -((0:ℝ) • v) := by
    rw [← h]
  rw [add_neg_cancel] at h2
  rw [add_assoc, add_neg_cancel, add_zero] at h2
  rw [h2]
