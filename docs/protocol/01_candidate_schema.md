# EXP-LOOP-003 Protocol: 01. Candidate Task Unit Schema

**Protocol Version**: `1.0.0`  
**Status**: FROZEN  
**Schema Implementation**: `lerm/candidate_schema.py`

## 1. Schema Definition

Each candidate task unit for EXP-LOOP-003 is defined by an immutable identity represented by `CandidateTaskUnit` dataclass.

| Field Name | Type | Allowed Values / Range | Required | Immutable | Validation Rule |
|---|---|---|---|---|---|
| `task_id` | `str` | Matching `^(CAND\|SWE-SM)-[A-Za-z0-9_\-]+$` | Yes | Yes | Non-empty regex-validated task identifier. Cannot match historical `HOLDOUT-001..004`. |
| `source_repository` | `str` | Registered repository name | Yes | Yes | Non-empty string corresponding to validated repo profile. |
| `source_commit` | `str` | 7–40 hex characters `^[0-9a-f]{7,40}$` | Yes | Yes | Valid git commit SHA of repository baseline. |
| `mutation_id` | `str` | Non-empty string | Yes | Yes | Unique mutation run identifier. Must be unique across pool. |
| `mutation_seed` | `int` | Integers $\ge 0$ | Yes | Yes | Explicit integer PRNG seed governing mutation operator choice. |
| `mutation_rule` | `str` | `ALLOWED_MUTATION_RULES` | Yes | Yes | Must belong to `{func_pm_ctrl_invert_if, func_pm_ctrl_shuffle, func_pm_remove_assign, func_pm_remove_cond, func_pm_remove_loop}`. |
| `original_file_paths` | `tuple[str, ...]` | Normalized paths | Yes | Yes | Tuple of target source file paths; must use forward slashes `/`. |
| `mutated_file_paths` | `tuple[str, ...]` | Normalized paths | Yes | Yes | Tuple of mutated source file paths; forward slashes `/`. |
| `baseline_state_id` | `str` | 64 hex characters `^[0-9a-f]{64}$` | Yes | Yes | SHA-256 hash of clean repository state. |
| `mutated_state_id` | `str` | 64 hex characters `^[0-9a-f]{64}$` | Yes | Yes | SHA-256 hash of repository state after applying patch. |
| `candidate_content_hash` | `str` | 64 hex characters `^[0-9a-f]{64}$` | Yes | Yes | SHA-256 hash of unified diff patch content. |
| `baseline_content_hash` | `str` | 64 hex characters `^[0-9a-f]{64}$` | Yes | Yes | SHA-256 hash of unmutated target file content. |
| `generation_timestamp` | `str` | ISO 8601 UTC timestamp | Yes | Yes | Format `YYYY-MM-DDTHH:MM:SSZ`. |
| `generator_version` | `str` | Non-empty string | Yes | Yes | SWE-smith commit SHA (e.g. `swe-smith-9b74ac0`). |
| `generator_config_hash` | `str` | 64 hex characters `^[0-9a-f]{64}$` | Yes | Yes | SHA-256 hash of complete generator parameter configuration. |
| `task_schema_version` | `str` | `"1.0.0"` | Yes | Yes | Strict version match. |
| `data_role` | `str` | `raw_candidate`, `calibration`, `primary` | Yes | Yes | Must match declared pipeline stage. |
| `historical_exposure` | `bool` | `False` | Yes | Yes | Must be strictly boolean `False` for fresh candidates. |
| `primary_exp_loop_003_eligible` | `bool` | `bool` | Yes | Yes | Cannot be `True` for historical tasks. Set `False` until admission. |
| `provenance` | `dict[str, Any]` | Non-empty mapping | Yes | Yes | Must contain `generator_version`, `generator_config_hash`, `timestamp`. |

## 2. Invariant Properties
1. Every instance is frozen (`@dataclass(frozen=True)`).
2. All path strings are normalized with forward slashes `/` across OS platforms.
3. Historical exposure is fail-closed: any attempt to set `historical_exposure=True` on a primary or calibration candidate triggers immediate rejection.
