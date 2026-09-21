# EXP-LOOP-003 Protocol: 10. Candidate Manifest Format

**Status**: FROZEN  
**Schema Implementation**: `holdout/tasks/_schema.yaml` and `lerm/candidate_schema.py`

## 1. Candidate Task Manifest Specification

Candidate manifests are serialized in strict YAML or JSON Lines format. Each entry must validate against `CandidateTaskUnit`:

```yaml
schema_version: "1.0.0"
manifest_id: "EXP-LOOP-003-CANDIDATES"
generated_at: "2026-09-21T12:00:00Z"
master_seed: 20260921
generator_commit: "9b74ac08118a85c39c356802f7961893af73e07f"
tasks:
  - id: "CAND-001"
    source_repository: "mewwts__addict.75284f95"
    source_commit: "75284f95b583ddf8c148bbcf469f3e4e9f7831d3"
    mutation_id: "mut_func_pm_remove_cond__ty8un4e6"
    mutation_seed: 42
    mutation_rule: "func_pm_remove_cond"
    original_file_paths:
      - "addict/addict.py"
    mutated_file_paths:
      - "addict/addict.py"
    baseline_state_id: "8c7d6e..." # 64-char SHA256
    mutated_state_id: "1f2e3d..." # 64-char SHA256
    candidate_content_hash: "f4b376ebfd87bbbfa8ee67dfe6f835d1190a01dfec90961166d1d92836419900"
    baseline_content_hash: "3b2a1c..." # 64-char SHA256
    generation_timestamp: "2026-09-21T12:00:00Z"
    generator_version: "swe-smith-9b74ac0"
    generator_config_hash: "8f03dc16a4e320f3e691ba73efcb0cf7925e04e963ecf6d9a9cf58a5c37eb61b"
    task_schema_version: "1.0.0"
    data_role: "raw_candidate"
    historical_exposure: false
    primary_exp_loop_003_eligible: false
    provenance:
      generator_version: "swe-smith-9b74ac0"
      generator_config_hash: "8f03dc16a4e320f3e691ba73efcb0cf7925e04e963ecf6d9a9cf58a5c37eb61b"
      timestamp: "2026-09-21T12:00:00Z"
```

## 2. Integrity Checks
- Manifests must not contain duplicate `task_id`, `mutation_id`, or `candidate_content_hash`.
- Any manifest with an unrecognized field or missing required field is rejected fail-closed.
