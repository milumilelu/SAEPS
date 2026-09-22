# Bias-correction audit

Development-only split-sample audit; the bias estimate uses the synthetic truth and is not a deployable estimator.

{
  "method": "development_truth_based_bias_shift_audit",
  "train_n": 50,
  "test_n": 50,
  "estimated_bias": -0.007725261981214535,
  "methods": {
    "raw": {
      "uncorrected_count": 16,
      "uncorrected_coverage": 0.32,
      "corrected_count": 13,
      "corrected_coverage": 0.26,
      "uncorrected_wilson": [
        0.20758216260657106,
        0.4581029730814369
      ],
      "corrected_wilson": [
        0.15871527493552606,
        0.3955315726484844
      ]
    },
    "saeps": {
      "uncorrected_count": 38,
      "uncorrected_coverage": 0.76,
      "corrected_count": 40,
      "corrected_coverage": 0.8,
      "uncorrected_wilson": [
        0.6258731624205748,
        0.8570260860300806
      ],
      "corrected_wilson": [
        0.6696289406777499,
        0.8875624998422372
      ]
    },
    "parameter_block": {
      "uncorrected_count": 16,
      "uncorrected_coverage": 0.32,
      "corrected_count": 13,
      "corrected_coverage": 0.26,
      "uncorrected_wilson": [
        0.20758216260657106,
        0.4581029730814369
      ],
      "corrected_wilson": [
        0.15871527493552606,
        0.3955315726484844
      ]
    }
  }
}