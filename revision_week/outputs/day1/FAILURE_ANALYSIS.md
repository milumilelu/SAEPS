# Retained failures and limitations

Historical/engineering failures:

[
  {
    "center": "burgers_57",
    "status": "CHECKPOINT_INVALID",
    "reason": "frozen center policy failed"
  },
  {
    "center": "burgers_61",
    "status": "CHECKPOINT_INVALID",
    "reason": "frozen center policy failed"
  },
  {
    "center": "burgers_63",
    "status": "CHECKPOINT_INVALID",
    "reason": "frozen center policy failed"
  },
  {
    "center": "allen_cahn_81",
    "status": "CHECKPOINT_INVALID",
    "reason": "frozen center policy failed"
  }
]

SO not improved: ['burgers_59', 'burgers_67']. No replacements or damping changes.

Historical raw states/absolute gradients absent for E0; T3 not replayed on these centers.
Adaptive budget failures and missing finite relative guarantees remain in each raw record.
No full repository completion claim; original workspace deletions are preserved.
