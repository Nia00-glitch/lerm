# LERM EXP-LOOP-003 — PHASE D FINAL AUDIT REPORT

**Lead Roles**: Lead Experimental Scientist, Causal Inference Auditor, Adversarial Research Engineer, Reproducibility Engineer  
**Date**: 2026-09-21  
**Operating Principle**: TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT  
**Protocol Phase**: EXP-LOOP-003 Phase D Execution  
**Final Gate Decision**: `PHASE D BLOCKED`

---

## 1. Environment

### Hardware Specifications
- **Operating System**: Microsoft Windows 11 Home Single Language, Version 10.0.26200, 64-bit
- **CPU**: AMD Ryzen 5 7530U with Radeon Graphics (6 Physical Cores, 12 Logical Processors)
- **RAM**: 16,097,540 KB Total Visible Memory (~15.35 GiB visible)
- **Execution Plane**: Native Host + Docker Desktop Linux containers via WSL2 (kernel 6.6.87.2-microsoft-standard-WSL2)

### Software & Tooling Versions
- **Python**: `Python 3.14.7`
- **Pip**: `pip 26.2.1 from C:\Python314\Lib\site-packages\pip (python 3.14)`
- **Git**: `git version 2.52.0.windows.1`
- **Docker**: `Docker version 29.6.2, build dfc4efb`
- **Docker Server Engine**: `Server Version 29.6.2`, `io.containerd.snapshotter.v1`, `runc version v1.3.6-0-g491b69ba`

### Key Research Dependencies
- `libcst`: `1.9.0`
- `astor`: `0.8.1`
- `tree-sitter`: `0.26.0`
- `swebench`: `4.1.0`
- `docker`: `7.2.0`
- `pytest`: `9.1.1`
- `numpy`: `2.5.2`
- `scipy`: `1.18.1`
- `pydantic`: `2.13.5`

---

## 2. Git Provenance

```bash
git rev-parse HEAD; git status --short; git branch --show-current; git log -1 --oneline
```
- **Commit Hash (HEAD)**: `6d8b0ae4f08971ae1b0e57a96013823918d18254`
- **Branch**: `main`
- **Latest Commit**: `6d8b0ae docs: publish final publication audit report and path resilience polish`
- **Working Tree**: Clean (zero uncommitted changes to codebase).

---

## 3. Generator Provenance

```bash
git -C swe-smith rev-parse HEAD; git -C swe-smith status --short; git -C swe-smith log -1 --oneline
```
- **SWE-smith Commit**: `9b74ac08118a85c39c356802f7961893af73e07f`
- **Working Tree**: Clean.
- **Log**: `9b74ac0 Add PHP language support (#233)`
- **Compliance**: Exactly matches frozen protocol requirement (`9b74ac08118a85c39c356802f7961893af73e07f`).

---

## 4. Protocol Provenance

### Generator Configuration
Specified in `docs/protocol/04_candidate_generation_config.md`:
```yaml
framework: "swe-smith"
commit: "9b74ac08118a85c39c356802f7961893af73e07f"
mode: "procedural"
language: "python"
max_entities_sampled: 10
max_bugs_per_entity: 1
interleave: false
timeout_per_repo_seconds: 120
```
- **Config Hash Registered**: `8f03dc16a4e320f3e691ba73efcb0cf7925e04e963ecf6d9a9cf58a5c37eb61b`

### Seed Hierarchy & Conflict Discovery
Authoritative definition in `docs/protocol/05_random_seed_policy.md`:
- `MASTER_SEED = 20260921`
- **Repository Sampling Seed Formula**: `(MASTER_SEED + 101) % 100000 = 61022`
- **Candidate Mutation Seed 1**: `(MASTER_SEED + 201) % 100000 = 61122`
- **Candidate Mutation Seed 2**: `(MASTER_SEED + 202) % 100000 = 61123`
- **Candidate Mutation Seed 3**: `(MASTER_SEED + 203) % 100000 = 61124`
- **Calibration Agent Seed Base**: `(MASTER_SEED + 500) % 100000 = 61421`

**UNRESOLVED SEED CONFLICT DISCOVERED**:
- `docs/protocol/02_repository_sampling_policy.md` (Line 51) and `reports/PHASE_C_AUDIT_REPORT.md` (Line 69) explicitly specify: `PRNG_SEED_REPO = 10001`.
- `docs/protocol/05_random_seed_policy.md` specifies `(MASTER_SEED + 101) % 100000 = 61022`.
- Per D0.5 guidelines: *“There must be exactly ONE authoritative seed definition for Phase D. If different repository documents/scripts contain conflicting seed values: STOP BEFORE GENERATION. Report: SEED_CONFLICT.”*

---

## 5. Candidate Generation Accounting

- **K_raw_target**: 30
- **K_generated**: 0
- **Status**: Generation halted before batch generation due to D0 Preflight Gate Failure.

No candidates were generated, cherry-picked, or replaced.

---

## 6. Validation

- **K_validated**: 0
- **K_rejected_validation**: 0
- **Status**: Validation was not reached due to hard stop at D0 Gate.

---

## 7. Calibration

- **K_entered_calibration**: 0
- **Stage 1 Trials Run**: 0
- **Stage 2 Trials Run**: 0
- **Status**: Calibration was not reached due to hard stop at D0 Gate.

---

## 8. Final Admission Accounting

```text
30 TARGET RAW CANDIDATES
      ↓
D0 PREFLIGHT GATE FAIL (SEED_CONFLICT & MISSING_REPOSITORIES)
      ↓
0 GENERATED
      ↓
0 VALIDATED
      ↓
0 CALIBRATION ELIGIBLE
      ↓
0 ADMITTED / 0 REJECTED
```

- **K_generated**: 0
- **K_validated**: 0
- **K_rejected_validation**: 0
- **K_entered_calibration**: 0
- **K_floor**: 0
- **K_ceiling**: 0
- **K_admitted**: 0
- **K_rejected_calibration**: 0

---

## 9. Deviations

No silent deviations or unauthorized overrides were introduced.

Documented Protocol Inconsistencies:
1. `SEED_CONFLICT`: Discrepancy between `docs/protocol/05_random_seed_policy.md` (`PRNG_SEED_REPO = 61022`) and `docs/protocol/02_repository_sampling_policy.md` / `reports/PHASE_C_AUDIT_REPORT.md` (`PRNG_SEED_REPO = 10001`).
2. `OFFLINE_REPOSITORY_POOL`: `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` are registered in SWE-smith profiles but not checked out locally on disk, preventing offline baseline execution.

---

## 10. Data Integrity

- Preflight Report: [D0_PREFLIGHT.md](file:///c:/Users/Arsh/.gemini/antigravity-ide/scratch/lerm/reports/phase-d/D0_PREFLIGHT.md)
- Candidate Manifest: Not generated (Generation halted).
- Repository Baseline Commit: `mewwts__addict.75284f95` verified at `75284f9593dfb929cadd900aff9e35e7c7aec54b`.

---

## 11. Treatment Contamination Audit

- **Treatment Trials Run in Phase D**: 0
- **Post-treatment Traces Read**: None
- **Verifier Feedback Leaked**: None
- **Evaluation Independence**: Verified. Zero treatment contamination.

---

## 12. Final Gate Decision

$$\mathbf{PHASE\ D\ BLOCKED}$$

### Reason for Halt
Under the governing scientific principle:
$$\mathbf{TRUTH\ >\ CAUSAL\ VALIDITY\ >\ INDEPENDENCE\ >\ STATISTICAL\ POWER\ >\ REPRODUCIBILITY\ >\ THROUGHPUT}$$

Execution strictly halted at **D0 Gate** per Absolute Stop Conditions #1, #2, and #7. The lead auditor refuses to silently edit seeds, bypass the offline repository requirement, or generate tasks on an ambiguous protocol state.
