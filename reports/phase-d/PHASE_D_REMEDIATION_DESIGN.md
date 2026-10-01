# LERM EXP-LOOP-003 — Phase D Protocol Remediation Design

**Lead Roles**: Lead Experimental Scientist, Causal Inference Auditor, Reproducibility Engineer, Adversarial Protocol Auditor, Research Infrastructure Engineer  
**Date**: 2026-09-21  
**Operating Principle**: **TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT**  
**Document Status**: `DESIGN AND AUDIT ONLY — NO GENERATION AUTHORIZED`

---

## Executive Summary

Phase D preflight (D0) demonstrated that while candidate schema, data firewall, and SWE-smith generator bit-reproducibility are green, the execution pipeline cannot proceed under the frozen protocol due to two critical empirical realities:
1. **Dependency Ineligibility of Multi-Repo Pool**: Repositories `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` fail baseline unit tests offline due to unpinned, floating third-party dependencies (`simplejson`, `tblib`, `diff-cover`, etc.). Neither repository provides an exact lockfile. Arbitrarily running `pip install` violates supply-chain reproducibility (Rules G5/G6), triggering deterministic exclusion under Protocol 02 §2 (`BASELINE_FAIL`).
2. **SWE-smith Checkout Deletion (`shutil.rmtree`)**: In SWE-smith commit `9b74ac08118a85c39c356802f7961893af73e07f`, `generate.py:L184` unconditionally executes `shutil.rmtree(repo)`. Running candidate generation erases the local checkout from disk, guaranteeing that subsequent offline ground-truth evaluators cannot access the repository.

This document designs the principled, non-invasive remediation across Parts A through E to restore experimental feasibility without compromising causal validity, independence, or historical firewall integrity.

---

## Part A — Repository Pool Remediation Strategy

### 1. Empirical Status of Repository Pool

| Repository Profile | Clean Baseline Status | Dependency Status | Offline Reproducibility | Exclusion Status (Protocol 02 §2) |
|---|---|---|---|---|
| `mewwts__addict.75284f95` | **10/10 PASS** (0.18s mean) | Pure Python, zero external deps | 100% verified offline | **ELIGIBLE** |
| `marshmallow-code__marshmallow.9716fc62` | **FAIL** (`simplejson` missing) | Floating `[project.optional-dependencies].tests` | Failed offline import | **EXCLUDED (`BASELINE_FAIL`)** |
| `sqlfluff__sqlfluff.50a1c4b6` | **FAIL** (`sqlfluff` / `tblib` missing) | Floating `dependencies` in `pyproject.toml` | Failed offline import | **EXCLUDED (`BASELINE_FAIL`)** |

### 2. Strategic Options

#### Option 1: Restrict EXP-LOOP-003 Pool to `mewwts__addict.75284f95` (Recommended)
- **Mechanism**: Amend Protocol 02 §3 to register `marshmallow` and `sqlfluff` under `EXCLUDED (BASELINE_FAIL / UNPINNED_DEPENDENCY)` and generate the $K=30$ candidate pool exclusively from `mewwts__addict.75284f95`.
- **Causal & Statistical Assessment**:
  - `addict` contains 23 code entities and yields dozens of valid AST mutations across all 5 allowed procedural mutation rules (`func_pm_ctrl_invert_if`, `func_pm_ctrl_shuffle`, `func_pm_remove_assign`, `func_pm_remove_cond`, `func_pm_remove_loop`).
  - Candidate independence is preserved at the function/method and diff content hash level (Protocol 12).
  - Eliminates all supply-chain contamination and external network dependencies.
  - Generates zero threat to causal inference: candidate tasks remain strictly independent and calibrated single-shot without treatment feedback.
- **Drawback**: Reduces repository diversity across the candidate pool to a single codebase.

#### Option 2: Pre-build Pinned Docker Testbeds for `marshmallow` and `sqlfluff`
- **Mechanism**: Build container images containing exact pinned wheels for `marshmallow` and `sqlfluff`, execute tests exclusively via `docker exec`.
- **Causal & Statistical Assessment**: Requires determining arbitrary version pins for unpinned repository dependencies, introducing researcher degrees of freedom.
- **Drawback**: Substantial delay and complexity; violates Protocol 02's requirement for lean offline reproducibility.

### 3. Remediation Decision
Adopt **Option 1**: Formally classify `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` as `EXCLUDED (BASELINE_FAIL)` in Protocol 02, and restrict candidate generation to `mewwts__addict.75284f95`.

---

## Part B — SWE-smith Execution Plane & Deletion Mitigation

### 1. Defect Analysis
In `swe-smith/swesmith/bug_gen/procedural/generate.py`:
```python
182:     total = process_with_timeout()
183: 
184:     shutil.rmtree(repo)
185:     print(f"Generated {total} bugs for {repo}.")
```
`shutil.rmtree(repo)` destroys the repository checkout directory at the end of every `main()` invocation.

### 2. Non-Invasive Mitigation Design
Under the hard constraint *“Do NOT modify SWE-smith unless explicitly authorized by frozen protocol”*, SWE-smith source code in `swe-smith/` must remain untouched (`git -C swe-smith status` clean at commit `9b74ac08118a85c39c356802f7961893af73e07f`).

#### Mitigation Architecture: Ephemeral Working Copy Wrapper
1. Maintain an immutable local reference clone of the repository at `.repo_cache/<repo_name>` or `<repo_name>.golden`.
2. Before invoking `swesmith.bug_gen.procedural.generate.main(repo, ...)`:
   - Verify `<repo_name>.golden` exists and is clean at pinned HEAD (`75284f9593dfb929cadd900aff9e35e7c7aec54b`).
   - Copy `<repo_name>.golden` $\rightarrow$ `./<repo_name>`.
3. Execute `main(repo, ...)`. SWE-smith mutates files, writes patches to `logs/bug_gen/<repo_name>/...`, and then executes `shutil.rmtree(repo)`.
4. Immediately post-generation:
   - Restore `./<repo_name>` from `<repo_name>.golden` via clean copy.
   - Verify `git -C ./<repo_name> rev-parse HEAD == 75284f95...` and `git status --short` is empty.
5. Result: SWE-smith executes unmodified, yet the repository remains fully present on disk for Phase D2 validation and baseline verification.

---

## Part C — Environment Architecture & Containerized Sandbox

### 1. Host Execution Plane (Procedural Generation & Validation)
- Candidate generation: Runs locally via LibCST AST modifiers in Python 3.14 with standard `resource` shim. Purely CPU-bound, bit-deterministic, offline.
- Baseline & Reference Repair Evaluator: Executes `pytest test_addict.py -q` in the restored `./mewwts__addict.75284f95` checkout. Baseline verified $< 0.20$s execution time.

### 2. Containerized Sandbox (Calibration & Primary Trials)
- Evaluation and single-shot calibration run inside the Docker container `oh-agent-server` or `openhands-app` with mounted project workspace `/workspace/project`.
- The agent has zero network access and zero verifier diagnostics during calibration.

---

## Part D — Historical Firewall & Trace Purity Invariants

### 1. Firewall Invariants (Phase B Gating)
- The historical firewall in `lerm/firewall.py` remains active and fail-closed:
  - Historical task IDs (`HOLDOUT-001..004`) cannot enter `calibration` or `primary`.
  - Byte-identical fixture content hashes matching historical holdouts trigger immediate `HISTORICAL_FIREWALL_BREACH`.
  - Non-boolean or missing `historical_exposure` flags fail closed.

### 2. Calibration Trace Purity (Protocol 06 & 13)
- `CandidatePool.check_treatment_purity`: Verifies candidate metadata contains zero treatment keys (`treatment_success`, `loop_retry_outcome`, `verifier_feedback`, `turn_count`, `post_treatment_trace`).
- All calibration trials are single-shot ($T=1$, `MAX_TURNS=1`), zero retry, zero feedback.

---

## Part E — Formal Protocol Amendments & Cryptographic Sealing Plan

### 1. Required Protocol Amendments
1. **`docs/protocol/02_repository_sampling_policy.md`**:
   - Reconcile `PRNG_SEED_REPO = 61022` (completed).
   - Reclassify `marshmallow` and `sqlfluff` from `ELIGIBLE` to `EXCLUDED (BASELINE_FAIL / UNPINNED_DEPENDENCY)`.
   - Update Table in §3 to mark `mewwts__addict.75284f95` as the sole eligible repository for EXP-LOOP-003.
2. **`docs/DEVIATIONS.md`**:
   - Register Deviation Item 8: Exclusion of `marshmallow` and `sqlfluff` due to unpinned dependencies failing clean offline baseline checkout.
   - Register Deviation Item 9: Ephemeral wrapper pattern for non-invasive handling of SWE-smith `shutil.rmtree` checkout cleanup.

### 2. Preregistration & Cryptographic Hashes
- Prior to D1 candidate generation, update and compute SHA-256 hashes for all amended protocol documents in `reports/phase-d/PROTOCOL_HASH_REGISTRY.md`.
- No candidate generation may proceed until D0 preflight is rerun from scratch and returns `STATUS: PASS`.

---

## Final Status Line

```text
=============================================================================
REMEDIATION DESIGN STATUS: COMPLETE — AWAITING FORMAL APPROVAL BEFORE RERUN
=============================================================================
```
