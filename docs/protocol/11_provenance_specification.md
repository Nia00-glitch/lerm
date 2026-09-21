# EXP-LOOP-003 Protocol: 11. Provenance Specification

**Status**: FROZEN  
**Principle**: Verifiable origin for every task artifact, preventing untracked, synthetic, or injected tasks.

## 1. Required Provenance Attributes

Every candidate task unit must include a `provenance` dictionary containing:
- `generator_version`: Git commit SHA of generator repository (`swe-smith-9b74ac08118a85c39c356802f7961893af73e07f`).
- `generator_config_hash`: SHA-256 hash of generation parameters.
- `timestamp`: UTC generation timestamp in ISO 8601 format.
- `source_repo_url`: Canonical git upstream URL of source repository.
- `source_commit`: Canonical git commit hash of checkout.

## 2. Validation & Anti-Tampering Rules
1. If `provenance` is empty or missing, `CandidateValidationError` is raised immediately.
2. If `provenance["generator_config_hash"] != candidate.generator_config_hash`, the candidate is rejected with `provenance_tampered`.
3. If `provenance` contains any treatment-related keys (`treatment_success`, `loop_verify_outcome`, etc.), `TreatmentLeakageError` is raised.
