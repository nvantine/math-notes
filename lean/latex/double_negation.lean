theorem double_negation (v : V) : -(-v) = v := by
  have h1 : v + (-v) = 0 := add_neg_cancel v
  have h2 : (-v) + (-(-v)) = 0 := add_neg_cancel (-v)
  rw [add_comm] at h1
  -- h1 : -v + v = 0
  -- h2 : -v + -(-v) = 0
  have := add_left_cancel (h1.trans h2.symm)
  exact this.symm
