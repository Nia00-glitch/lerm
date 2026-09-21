# EXP-LOOP-003 Protocol: 09. Candidate Rejection Taxonomy

**Status**: FROZEN  
**Implementation**: `lerm/candidate_pool.py`

## 1. Frozen Rejection Categories

Every rejected candidate is deterministically classified into one of the following mutually exclusive categories:

| Category Key | Rejection Trigger | Fail-Closed Action |
|---|---|---|
| `baseline_failure` | Step B of verification chain fails (baseline tests do not exit 0). | Discard candidate. Repo baseline is invalid. |
| `mutation_no_effect` | Step D fails (mutation does not cause test suite failure). | Discard candidate. Mutation had no semantic impact. |
| `infrastructure_failure`| Test suite exits with OOM (137), timeout, missing binary, or OS error. | Discard candidate. Hardware/environment artifact. |
| `evaluator_failure` | SyntaxError or exception thrown by test harness itself. | Discard candidate. Test fixture broken. |
| `reference_repair_failure` | Step F fails (reference repair patch does not restore exit 0). | Discard candidate. Task is unrepairable. |
| `reset_failure` | Step H fails (reset file hash does not match mutated fixture hash). | Discard candidate. State mutation was non-reversible. |
| `duplicate_mutation` | Candidate mutation ID already exists in candidate pool. | Reject duplicate. |
| `duplicate_diff` | Patch diff content hash already exists under a different mutation ID. | Reject semantic duplicate. |
| `duplicate_config` | Candidate generated with same (repo, commit, rule, seed) tuple. | Reject duplicate configuration. |
| `provenance_tampered`| Provenance config hash does not match candidate config hash. | Reject as unverified/tampered. |
| `provenance_missing` | Candidate lacks required generator metadata and signature. | Reject as missing provenance. |
| `historical_firewall_breach`| Candidate matches historical ID `HOLDOUT-001..004` or historical fixture hash. | Quarantined immediately. |
| `treatment_leakage` | Candidate metadata contains treatment outcomes or loop feedback. | Quarantined. Pipeline breach. |
| `hash_mismatch` | Declared content hash does not match SHA-256 of patch content. | Reject as corrupted artifact. |
| `ambiguous` | Flaky tests; non-deterministic pass/fail across 5 repeated runs. | Discard candidate. |
| `other` | Schema violation (invalid types, missing required fields). | Reject candidate. |
