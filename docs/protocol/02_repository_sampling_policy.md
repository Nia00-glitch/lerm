# EXP-LOOP-003 Protocol: 02. Source-Repository Sampling Policy

**Status**: FROZEN  
**Principle**: Causal independence from treatment outcomes. No post-hoc cherry-picking.

## 1. Repository Eligibility Criteria

A source repository is eligible for candidate sampling if and only if it satisfies all of the following conditions:

1. **Language Eligibility**:
   - Pure Python 3.9+ codebase.
   - Fully parsable by LibCST and Python AST.

2. **Testability & Reproducibility Requirements**:
   - Clean, reproducible test suite executable offline via `pytest`.
   - Baseline test execution time $< 10.0$ seconds for unit test suite.
   - Zero flaky tests (10 consecutive baseline runs must yield 10 identical exit codes `0`).
   - Zero external network dependencies during test execution (offline isolated execution).

3. **Repository Size Limits**:
   - Total source code size $< 50$ MB.
   - Source entities (functions/classes) $\ge 10$ and $\le 5,000$.

4. **License Constraints**:
   - Permissive open-source license (MIT, Apache 2.0, BSD-2/3-Clause).

5. **Commit Selection Rule**:
   - Must use a fixed, pinned git commit hash corresponding to a verified release tag or stable HEAD.
   - No rolling HEAD or branch names permitted.

## 2. Deterministic Exclusion Rules

Repositories are excluded if:
- `UNREGISTERED_IN_SWESMITH`: Repository is not defined in `swesmith/profiles/python.py` (e.g. `pvlib`).
- `BASELINE_FAIL`: Clean checkout fails any test.
- `TIMEOUT_EXCEEDED`: Test suite takes $> 10$ seconds.
- `NETWORK_DEPENDENCY`: Tests require internet access.
- `ENV_INCOMPATIBLE`: Requires non-standard system C libraries unavailable in the container runtime.

## 3. Verified Repository Pool

| Repository Name | Commit SHA | Unit Tests | Baseline Runtime | Status | Notes |
|---|---|---|---|---|---|
| `mewwts__addict.75284f95` | `75284f95` | 128 passed | 0.33s | **ELIGIBLE** | Verified 100% reproducible baseline. |
| `marshmallow-code__marshmallow.9716fc62` | `9716fc62` | 421 entities | 2.15s | **ELIGIBLE** | Verified compatible AST parsing. |
| `sqlfluff__sqlfluff.50a1c4b6` | `50a1c4b6` | 3126 entities | 4.80s | **ELIGIBLE** | High-complexity SQL parsing library. |
| `pvlib/pvlib-python` | N/A | N/A | N/A | **EXCLUDED** | Reason: `UNREGISTERED_IN_SWESMITH`. |

## 4. Sampling Randomization Seed
- Candidate repositories are indexed deterministically.
- Selection order across repositories is fixed prior to candidate generation using `PRNG_SEED_REPO = 10001`.
