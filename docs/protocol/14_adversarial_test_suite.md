# EXP-LOOP-003 Protocol: 14. Adversarial Test Suite Documentation

**Status**: FROZEN  
**Test Suite File**: `tests/test_candidate_adversarial.py`  
**Execution Command**: `python -m pytest tests/test_candidate_adversarial.py -v`  
**Result**: 20 / 20 Tests Passed in 0.15s.

## 1. Attack Vectors and Results

| # | Attack Vector Description | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| 1 | Historical task injected into calibration (`HOLDOUT-001`) | Blocked by firewall (`historical_firewall_breach`) | Blocked (`historical_firewall_breach`) | **PASS** |
| 2 | Historical task injected into primary (`HOLDOUT-002`) | Blocked by firewall (`historical_firewall_breach`) | Blocked (`historical_firewall_breach`) | **PASS** |
| 3 | Fresh task with fake provenance | Blocked (`provenance_tampered`) | Blocked (`provenance_tampered`) | **PASS** |
| 4 | Fresh task with missing provenance | Schema validation raises `CandidateValidationError` | Raised `CandidateValidationError` | **PASS** |
| 5 | Fresh task with altered provenance | Blocked (`provenance_tampered`) | Blocked (`provenance_tampered`) | **PASS** |
| 6 | Candidate copied from historical fixture | Direct firewall fixture check raises `FirewallViolation` | Raised `FirewallViolation` | **PASS** |
| 7 | Candidate with one-byte source perturbation | Blocked (`hash_mismatch`) | Blocked (`hash_mismatch`) | **PASS** |
| 8 | Duplicate mutation | Blocked (`duplicate_mutation`) | Blocked (`duplicate_mutation`) | **PASS** |
| 9 | Same mutation under different ID | Blocked (`duplicate_diff`) | Blocked (`duplicate_diff`) | **PASS** |
| 10 | Treatment-success injected into metadata | Blocked (`treatment_leakage`) | Blocked (`treatment_leakage`) | **PASS** |
| 11 | Calibration result injected into generator | Blocked (`treatment_leakage`) | Blocked (`treatment_leakage`) | **PASS** |
| 12 | Candidate with missing mutation ID | Schema validation raises `CandidateValidationError` | Raised `CandidateValidationError` | **PASS** |
| 13 | Candidate with mismatched commit format | Schema validation raises `CandidateValidationError` | Raised `CandidateValidationError` | **PASS** |
| 14 | Candidate with mismatched content hash format | Schema validation raises `CandidateValidationError` | Raised `CandidateValidationError` | **PASS** |
| 15 | Candidate whose baseline already fails | Chain rejected (`baseline_failure`) | Rejected (`baseline_failure`) | **PASS** |
| 16 | Candidate mutation produces no failure | Chain rejected (`mutation_no_effect`) | Rejected (`mutation_no_effect`) | **PASS** |
| 17 | Candidate failure is infrastructure-only | Chain rejected (`infrastructure_failure`) | Rejected (`infrastructure_failure`) | **PASS** |
| 18 | Reference repair does not restore PASS | Chain rejected (`reference_repair_failure`) | Rejected (`reference_repair_failure`) | **PASS** |
| 19 | Candidate reset hash differs | Chain rejected (`reset_failure`) | Rejected (`reset_failure`) | **PASS** |
| 20 | Candidate generated with same seed twice | Blocked (`duplicate_config`) | Blocked (`duplicate_config`) | **PASS** |
