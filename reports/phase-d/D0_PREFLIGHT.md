# LERM EXP-LOOP-003 Phase D: D0 Preflight Report

**Lead Roles**: Lead Experimental Scientist, Causal Inference Auditor, Adversarial Research Engineer, Reproducibility Engineer  
**Date**: 2026-09-21  
**Operating Principle**: TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT  
**Protocol Phase**: D0 Execution Preflight  
**Overall Status**: `STATUS: FAIL`

---

## Executive Summary & Stop Notice

During the execution of the Phase D Preflight (D0), two blocking failures and protocol violations were empirically discovered:
1. **`SEED_CONFLICT`**: Direct contradiction between `docs/protocol/05_random_seed_policy.md` (which mandates hierarchical derivation from `MASTER_SEED = 20260921`, yielding `PRNG_SEED_REPO = 61022`) and `docs/protocol/02_repository_sampling_policy.md` / `reports/PHASE_C_AUDIT_REPORT.md` (which specify `PRNG_SEED_REPO = 10001`). Per the frozen protocol: *“If different repository documents/scripts contain conflicting seed values: STOP BEFORE GENERATION. Report: SEED_CONFLICT... Do not choose whichever value appears convenient. Do not silently edit the seed.”*
2. **Missing Source Repositories & Offline Requirement Violation**: Repositories `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` are not present locally on disk. Under the offline isolation constraint of Protocol 02, candidate generation and baseline test execution cannot proceed without unauthorized network access.

Per **Absolute Stop Conditions #1, #2, and #7**, execution is immediately halted at the **D0 Gate**. No candidate generation (D1), validation (D2), or calibration (D3) will occur.

---

## D0.1 Git Provenance

### Verification Command
```bash
git rev-parse HEAD; git status --short; git branch --show-current; git log -1 --oneline
```

### Raw Output
```text
6d8b0ae4f08971ae1b0e57a96013823918d18254
main
6d8b0ae docs: publish final publication audit report and path resilience polish
```

### Interpretation
- **Target HEAD**: `6d8b0ae4f08971ae1b0e57a96013823918d18254`
- **Working Tree**: Completely clean (zero uncommitted files).
- **Branch**: `main`.
- **Status**: `PASS`.

---

## D0.2 Runtime Environment

### Verification Commands & Raw Evidence

#### 1. Software Versions
```powershell
python --version; pip --version; docker --version; git --version
```
```text
Python 3.14.7
pip 26.2.1 from C:\Python314\Lib\site-packages\pip (python 3.14)
Docker version 29.6.2, build dfc4efb
git version 2.52.0.windows.1
```

#### 2. Hardware & Operating System
```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, TotalVisibleMemorySize, FreePhysicalMemory | Format-List
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List
```
```text
Caption                : Microsoft Windows 11 Home Single Language
Version                : 10.0.26200
OSArchitecture         : 64-bit
TotalVisibleMemorySize : 16097540
FreePhysicalMemory     : 2282480

Name                      : AMD Ryzen 5 7530U with Radeon Graphics         
NumberOfCores             : 6
NumberOfLogicalProcessors : 12
```

#### 3. Key Dependencies
- `libcst`: `1.9.0`
- `astor`: `0.8.1`
- `tree-sitter`: `0.26.0`
- `swebench`: `4.1.0`
- `docker`: `7.2.0`
- `pytest`: `9.1.1`
- `numpy`: `2.5.2`
- `scipy`: `1.18.1`
- `pydantic`: `2.13.5`

### Interpretation
The hardware platform is an AMD Ryzen 5 7530U (6C/12T, 16GB RAM) running Windows 11 64-bit with Docker Desktop WSL2 backend.  
- **Status**: `PASS`.

---

## D0.3 SWE-smith Provenance

### Verification Commands
```bash
git -C swe-smith rev-parse HEAD; git -C swe-smith status --short; git -C swe-smith log -1 --oneline
```

### Raw Output
```text
9b74ac08118a85c39c356802f7961893af73e07f
9b74ac0 Add PHP language support (#233)
```

### Interpretation
The local `swe-smith` checkout matches exactly the frozen commit `9b74ac08118a85c39c356802f7961893af73e07f` with a clean working tree.  
- **Status**: `PASS`.

---

## D0.4 Generator Configuration

### Verification
Core configuration registered in `docs/protocol/04_candidate_generation_config.md`:
```yaml
candidate_generator:
  framework: "swe-smith"
  commit: "9b74ac08118a85c39c356802f7961893af73e07f"
  mode: "procedural"
  language: "python"
  max_entities_sampled: 10
  max_bugs_per_entity: 1
  interleave: false
  timeout_per_repo_seconds: 120
```

Registered canonical hash:
`CONFIG_HASH = "8f03dc16a4e320f3e691ba73efcb0cf7925e04e963ecf6d9a9cf58a5c37eb61b"`  
- **Status**: `PASS`.

---

## D0.5 Seed Verification & Conflict Report

### STOP TRIGGER: `SEED_CONFLICT`

#### 1. Authoritative Master Seed Hierarchy Spec (`docs/protocol/05_random_seed_policy.md`)
```markdown
All random operations in EXP-LOOP-003 derive hierarchically from a single preregistered master seed:
`MASTER_SEED = 20260921`

| Subsystem | Derived Seed Formula | Value | Purpose |
|---|---|---|---|
| **Repository Sampling** | `(MASTER_SEED + 101) % 100000` | `61022` | Shuffling repository order. |
| **Candidate Mutation Seed 1** | `(MASTER_SEED + 201) % 100000` | `61122` | Generating Candidate Batch A. |
| **Candidate Mutation Seed 2** | `(MASTER_SEED + 202) % 100000` | `61123` | Generating Candidate Batch B. |
| **Candidate Mutation Seed 3** | `(MASTER_SEED + 203) % 100000` | `61124` | Generating Candidate Batch C. |
| **Calibration Agent Seed Base**| `(MASTER_SEED + 500) % 100000` | `61421` | Base seed for Turn 1 single-shot agent sampling. |
```

#### 2. Conflicting Protocol Specification (`docs/protocol/02_repository_sampling_policy.md`, Line 51)
```markdown
## 4. Sampling Randomization Seed
- Candidate repositories are indexed deterministically.
- Selection order across repositories is fixed prior to candidate generation using `PRNG_SEED_REPO = 10001`.
```

#### 3. Conflicting Audit Report (`reports/PHASE_C_AUDIT_REPORT.md`, Line 69)
```markdown
- Sampling order: Deterministically permuted using `PRNG_SEED_REPO = 10001`. Zero subjective selection.
```

#### Detailed Conflict Analysis
- **File 1**: `docs/protocol/05_random_seed_policy.md` mandates `PRNG_SEED_REPO = 61022` (derived hierarchically as `(20260921 + 101) % 100000`).
- **File 2**: `docs/protocol/02_repository_sampling_policy.md` mandates `PRNG_SEED_REPO = 10001`.
- **File 3**: `reports/PHASE_C_AUDIT_REPORT.md` asserts `PRNG_SEED_REPO = 10001`.
- **Deviation Status**: `docs/DEVIATIONS.md` contains NO registered entry for this seed discrepancy.
- **Rule Violated**: *“There must be exactly ONE authoritative seed definition for Phase D. If different repository documents/scripts contain conflicting seed values: STOP BEFORE GENERATION. Report: SEED_CONFLICT with: file, conflicting value, expected value, exact evidence. Do not choose whichever value appears convenient. Do not silently edit the seed.”*
- **Status**: `FAIL (SEED_CONFLICT)`.

---

## D0.6 Repository Pool Verification

### Verification Command
```powershell
python -c "import os; print('mewwts exists:', os.path.exists('mewwts__addict.75284f95')); print('marshmallow exists:', os.path.exists('marshmallow-code__marshmallow.9716fc62')); print('sqlfluff exists:', os.path.exists('sqlfluff__sqlfluff.50a1c4b6'))"
```

### Raw Output
```text
mewwts exists: True
marshmallow exists: False
sqlfluff exists: False
```

### Verification Findings
1. `mewwts__addict.75284f95`:
   - Present locally at `C:\Users\Arsh\.gemini\antigravity-ide\scratch\lerm\mewwts__addict.75284f95`.
   - Baseline unit tests: 128 passed in 0.33s.
   - Offline runnable: Verified.
2. `marshmallow-code__marshmallow.9716fc62`:
   - NOT present locally on disk.
   - Requires network cloning via GitHub mirror (`swesmith.profiles.base.clone()`), violating Protocol 02 Section 1 ("Zero external network dependencies during test execution").
3. `sqlfluff__sqlfluff.50a1c4b6`:
   - NOT present locally on disk.
   - Baseline test execution and runtime cannot be verified offline.
- **Status**: `FAIL (MISSING_REPOSITORIES)`.

---

## D0.7 Docker / Sandbox Verification

### Verification Command
```bash
docker run --rm public.ecr.aws/docker/library/python@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb python -c "import sys; print('Docker Python execution verified:', sys.version)"
```

### Raw Output
```text
Docker Python execution verified: 3.13.12 (main, Mar 16 2026, 23:05:54) [GCC 12.2.0]
```

### Interpretation
Docker container engine successfully instantiated an isolated container, executed Python code, and returned exit code `0`.  
- **Status**: `PASS`.

---

## D0.8 OpenHands / OmniRoute / Model Verification

### Verification Commands & Raw Output

#### 1. OpenHands Server
```powershell
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:3000', timeout=3).getcode())"
```
```text
200
```
OpenHands server container `openhands-app` is healthy and listening on port 3000.

#### 2. OmniRoute Endpoint
```powershell
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:20128/v1/models', timeout=3).getcode())"
```
```text
urllib.error.URLError: <urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>
```
OmniRoute proxy is NOT running on port 20128, and `OMNIROUTE_API_KEY` is unset in `.env`.

#### 3. LLM Model Endpoint
Testing OpenRouter via direct OpenHands configured credentials:
```powershell
python test_or_model.py
```
```text
Found key: True
Model thinkingmachines/inkling-small-20260730:free: SUCCESS! Returned model: thinkingmachines/inkling-small:free
Model thinkingmachines/inkling-small:free: SUCCESS! Returned model: thinkingmachines/inkling-small:free
Model thinkingmachines/inkling-small-20260730: SUCCESS! Returned model: thinkingmachines/inkling-small
Model openrouter/free: SUCCESS! Returned model: thinkingmachines/inkling-small:free
```

### Interpretation
OpenRouter API model execution is functional via OpenHands profile `thinkingmachines/inkling-small:free`, but OmniRoute local service is down.  
- **Status**: `AMBIGUOUS / BLOCKED ON OMNIROUTE`.

---

## D0 Gate Decision

```text
=============================================================================
FINAL PREFLIGHT STATUS: STATUS: FAIL
=============================================================================
```

### Absolute Stop Conditions Tripped:
1. **Condition 1**: Protocol files conflict materially (`05_random_seed_policy.md` vs `02_repository_sampling_policy.md`).
2. **Condition 2**: Seed definitions conflict (`SEED_CONFLICT`: `61022` vs `10001`).
3. **Condition 7**: Target candidate repositories `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` are missing from the local offline execution plane.

**In strict accordance with the EXP-LOOP-003 Phase D Protocol, execution is STOPPED before candidate generation.**
