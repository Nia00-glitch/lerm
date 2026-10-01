# LERM EXP-LOOP-003 — Final Pre-D1 Design Approval Audit

**Lead Roles**: Lead Experimental Scientist, Causal Inference Auditor, Reproducibility Engineer, Adversarial Research Engineer, Experimental Protocol Reviewer  
**Date**: 2026-09-21  
**Operating Principle**: **TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT**  
**Document Status**: `FINAL AUDIT REPORT — FORMAL VERDICT`  

---

## Executive Summary

Following the completion of the Phase D Remediation Design ([PHASE_D_REMEDIATION_DESIGN.md](file:///c:/Users/Arsh/.gemini/antigravity-ide/scratch/lerm/reports/phase-d/PHASE_D_REMEDIATION_DESIGN.md)), this audit provides an adversarial, evidence-grounded review of the proposal to exclude `marshmallow` and `sqlfluff` and restrict candidate generation for EXP-LOOP-003 exclusively to `mewwts__addict.75284f95` using an ephemeral golden-copy wrapper around SWE-smith.

While the golden-copy lifecycle test passes completely, the seed hierarchy is fully verified, and historical firewall integrity is 100% fail-closed, **the proposed single-repository remediation FAILS Gate 2 (K=30 Capacity Audit)**:
Under the frozen rules of Protocol 12 §1 (Target Function / Method Level independence) and Protocol 04 (`max_bugs_per_entity: 1`), `mewwts__addict.75284f95` contains only **7** mutable functions across all 5 allowed procedural mutation operators, and yields at most **20** total single-pass AST mutations across the entire codebase. 

Because the independence-filtered upper bound ($K \le 7$ under Protocol 12 §1, or $K \le 20$ under unrestricted entity-rule pairs) is strictly less than the required fixed candidate pool of $K=30$, **the single-repository design cannot supply the required pool without violating the frozen independence specification**.

In accordance with the governing principle (*Truth > Throughput*), this audit **REJECTS** authorization of Phase D1 candidate generation and halts execution.

---

## GATE 1 — 3-Repository to 1-Repository Change Audit

### 1. Analysis of Protocol Questions

#### Question 1: Was repository diversity part of the registered design?
**Answer: YES.**  
In the Phase C Candidate-Generation Protocol Freeze (`reports/PHASE_C_AUDIT_REPORT.md` and `docs/protocol/02_repository_sampling_policy.md`), 3 distinct repositories were registered:
- `mewwts__addict.75284f95` (lightweight dictionary wrapper, 23 entities)
- `marshmallow-code__marshmallow.9716fc62` (complex serialization/validation framework, 421 entities)
- `sqlfluff__sqlfluff.50a1c4b6` (large-scale SQL parsing/linting engine, 3,126 entities)

Protocol 02 §4 explicitly established `PRNG_SEED_REPO = 61022` for the purpose of *"Shuffling repository order"*, and Protocol 05 established 3 distinct candidate mutation seeds (`61122`, `61123`, `61124`) for Candidate Batches A, B, and C. The experimental design intended to sample across diverse architectural paradigms to prevent findings from reflecting idiosyncratic features of a single codebase.

#### Question 2: Was K=30 defined across repositories or independently of repository count?
**Answer: Independently of repository count, based on statistical power requirements.**  
Protocol 06 §3 (*Post-Calibration Handling: Design C*) defines $K=30$ as a fixed global candidate pool size:
> *"A fixed initial candidate pool of $K=30$ deterministically generated candidates is evaluated in preregistered sequence."*

The sample size $K=30$ was dictated by statistical calibration power (Protocol 16: Wilson score confidence interval width, screening power under the $N_1=10, N=20$ sequential calibration policy to yield $N_{\text{admitted}} \approx 10..15$ balanced primary tasks). While the three candidate batches ($3 \times 10 = 30$) corresponded to the 3 registered repositories, $K=30$ represents the absolute minimum candidate pool required to maintain causal identification and statistical power for EXP-LOOP-003.

#### Question 3: Does exclusion of two repositories trigger replacement?
**Answer: NO. Replacement is strictly forbidden under frozen rules.**  
Protocol 02 §2 establishes deterministic exclusion rules (`UNREGISTERED_IN_SWESMITH`, `BASELINE_FAIL`, `TIMEOUT_EXCEEDED`, `NETWORK_DEPENDENCY`, `ENV_INCOMPATIBLE`). When a repository fails baseline tests, its deterministic classification is `BASELINE_FAIL`.
The protocol contains zero backup or fallback candidate repositories. Ad-hoc searching for, testing, and introducing replacement repositories at Phase D execution time would introduce unconstrained researcher degrees of freedom, violate protocol freeze, and invalidate preregistration.

#### Question 4: If replacement is not possible, can the remaining repository constitute the primary pool?
**Answer: ONLY IF it satisfies all structural, statistical, and independence constraints.**  
Protocol 02 §2 permits the exclusion of invalid repositories. However, for the remaining repository (`mewwts__addict.75284f95`) to legitimately supply the primary pool, it must possess sufficient structural capacity to generate $\ge 30$ independent candidates under the frozen rules of Protocol 03, 04, and 12. As established in Gate 2 below, it empirically fails this requirement.

#### Question 5: Does this alter the population to which the result can legitimately generalize?
**Answer: YES. It dramatically restricts the inference population.**  

### 2. Methodological Separation of Inference Layers

| Dimension | Multi-Repository Design (Registered) | Single-Repository Design (`addict` only) | Scientific Impact |
|---|---|---|---|
| **Task-Level Independence** | Tasks span 3 separate codebases and disparate modules | Tasks all reside within a single 160-line file (`addict.py`) | Tasks share the same class scope and naming conventions |
| **Repository-Level Diversity** | High (Dictionary, Serialization, SQL Parsing) | **Zero** (Dictionary subclass only) | Eliminates all cross-codebase variability |
| **Causal Identification** | Unbiased A/B contrast (`loop_verify` vs `loop_retry`) | Unbiased A/B contrast (`loop_verify` vs `loop_retry`) | Internal validity preserved; external validity collapsed |
| **External Validity / Scope** | Python library tooling generally | Small dictionary wrappers only | Findings cannot generalize to broader SWE tasks |

---

## GATE 2 — K=30 Capacity Audit

### 1. Definition of the Exact Independence Key

Under Protocol 12 §1, the statistical unit of independence is explicitly frozen at the **Target Function / Method Level**:
```text
INDEPENDENCE_KEY_STRICT = (source_repository, source_file, target_function_or_method)
```
Protocol 12 §1 explicitly mandates:
> *"No two candidate tasks in the pool may mutate the same function, method, or class block within a repository. No two tasks may share identical diff lines or overlapping patch chunks."*

Under the generator settings in Protocol 04 §1:
```yaml
candidate_generator:
  max_entities_sampled: 10
  max_bugs_per_entity: 1
  interleave: false
  timeout_per_repo_seconds: 120
```
`max_bugs_per_entity: 1` deterministically restricts SWE-smith to at most one candidate per code entity.

Under Protocol 12 §2, exact and semantic deduplication checks are enforced:
```text
INDEPENDENCE_KEY_DEDUP = (mutation_id, unified_diff_sha256, (repo, commit, mutation_rule, seed))
```

### 2. Empirical AST Analysis of `mewwts__addict.75284f95`

An exhaustive AST and LibCST analysis was executed across the clean checkout of `mewwts__addict.75284f95` (commit `75284f9593dfb929cadd900aff9e35e7c7aec54b`).

#### Total Extracted Entities: 23
The repository contains exactly one source module (`addict/addict.py`) with 23 code entities:
1. `Dict` (`ClassDef`)
2. `__init__` (`FunctionDef`)
3. `__setattr__` (`FunctionDef`)
4. `__setitem__` (`FunctionDef`)
5. `__add__` (`FunctionDef`)
6. `_hook` (`FunctionDef`)
7. `__getattr__` (`FunctionDef`)
8. `__missing__` (`FunctionDef`)
9. `__delattr__` (`FunctionDef`)
10. `to_dict` (`FunctionDef`)
11. `copy` (`FunctionDef`)
12. `deepcopy` (`FunctionDef`)
13. `__deepcopy__` (`FunctionDef`)
14. `update` (`FunctionDef`)
15. `__getnewargs__` (`FunctionDef`)
16. `__getstate__` (`FunctionDef`)
17. `__setstate__` (`FunctionDef`)
18. `__or__` (`FunctionDef`)
19. `__ror__` (`FunctionDef`)
20. `__ior__` (`FunctionDef`)
21. `setdefault` (`FunctionDef`)
22. `freeze` (`FunctionDef`)
23. `unfreeze` (`FunctionDef`)

#### Entities Susceptible to Allowed Procedural Mutation Rules (Protocol 03 §1)
Filtering against the 5 frozen procedural operators yields:
- `func_pm_ctrl_invert_if`: 2 eligible entities (`__init__`, `update`)
- `func_pm_ctrl_shuffle`: 4 eligible entities (`__init__`, `to_dict`, `update`, `freeze`)
- `func_pm_remove_assign`: 5 eligible entities (`__init__`, `__setitem__`, `to_dict`, `update`, `setdefault`)
- `func_pm_remove_cond`: 7 eligible entities (`__init__`, `__setitem__`, `_hook`, `to_dict`, `update`, `setdefault`, `freeze`)
- `func_pm_remove_loop`: 4 eligible entities (`__init__`, `to_dict`, `update`, `freeze`)

**Total unique mutable entities across all allowed rules**: Exactly **7** functions:
`{'__init__', '__setitem__', '_hook', 'freeze', 'setdefault', 'to_dict', 'update'}`.

### 3. Quantitative Capacity Audit Results

```text
=============================================================================
K=30 CAPACITY AUDIT METRICS FOR mewwts__addict.75284f95
=============================================================================
1. Potential raw mutations (exhaustive multi-seed test across 102 seeds):
   - Total raw diffs generated: 181
   - Severe clustering:
     * Entity '__init__':   84 diffs (46.4% of all mutations)
     * Entity '__setitem__': 35 diffs (19.3% of all mutations)
     * Entity 'update':      33 diffs (18.2% of all mutations)
     * Entity 'to_dict':     22 diffs (12.2% of all mutations)
     * Entity 'freeze':       3 diffs (1.7%)
     * Entity '_hook':        2 diffs (1.1%)
     * Entity 'setdefault':   2 diffs (1.1%)

2. Structurally valid single-pass mutations across allowed operators:
   - Total unique (entity, operator) AST rewrites: 20
   - Breakdown:
     * func_pm_ctrl_invert_if: 2
     * func_pm_ctrl_shuffle:   3
     * func_pm_remove_assign:  5
     * func_pm_remove_cond:    7
     * func_pm_remove_loop:    3

3. Independence-filtered candidates:
   - Under Protocol 12 §1 (Target Function Level):
     Upper bound = 7 independent tasks. (7 < 30 -> INSUFFICIENT)
   - Under Protocol 04 §1 (max_bugs_per_entity: 1):
     Upper bound = 7 independent tasks. (7 < 30 -> INSUFFICIENT)
   - Under Protocol 12 §3 (Distinct classes/modules):
     Upper bound = 1 class / 1 module.   (1 < 30 -> INSUFFICIENT)
   - Under unrestricted (entity, operator) pairs:
     Upper bound = 20 unique pairs.      (20 < 30 -> INSUFFICIENT)
=============================================================================
```

### 4. Independence Audit Finding

Generating $K=30$ candidates from `mewwts__addict.75284f95` is **mathematically impossible** without blatantly violating Protocol 12 §1 and §3. 
To reach 30 candidates, an experimenter would be forced to sample approximately 14 perturbations of `__init__`, 6 of `__setitem__`, 5 of `update`, and 4 of `to_dict`. These tasks would share identical functions, overlapping code lines, and clustered failure modes, completely destroying statistical unit independence and inducing an intraclass correlation $\rho \approx 1.0$.

Per the instructions of Gate 2:
> *"If the upper bound is <30: STOP. Do not generate a smaller arbitrary pool. Do not reduce K silently."*

**Verdict: STOP. K=30 CAPACITY INSUFFICIENT.**

---

## GATE 3 — Golden Copy Lifecycle Test

To ensure exhaustive empirical documentation, the golden-copy lifecycle wrapper was tested on a disposable copy with non-experimental parameters.

### 1. Test Conditions & Environment
- **Platform**: Windows 11 Home (NTFS file system).
- **Target Repository**: `mewwts__addict.75284f95`.
- **SWE-smith Commit**: `9b74ac08118a85c39c356802f7961893af73e07f` (clean, unmodified).
- **NTFS Consideration**: On Windows, Git marks `.git/objects/pack/*` read-only (`0444`). Calling unmodified `shutil.rmtree(repo)` causes `PermissionError: [WinError 5] Access is denied` unless write permissions (`stat.S_IWRITE`) are recursively applied to the working copy prior to execution. The wrapper handles this cleanly.

### 2. Empirical Verification Results

```text
=== GATE 3: GOLDEN COPY LIFECYCLE TEST RESULTS ===
BEFORE GENERATION:
  Golden commit:            75284f9593dfb929cadd900aff9e35e7c7aec54b
  Golden git status:        CLEAN
  Golden state hash:        28921257f5b7e4b1fef370603a89fa3f89fcb76e0ac564072019c5e0d0d39922

DURING GENERATION (Running unmodified SWE-smith):
  Artifacts inside repo:    0
  Artifacts outside repo:   18 files in logs/bug_gen/mewwts__addict.75284f95/...
  Generated diffs:          9 bug patches (.diff)
  Generated metadata:       9 metadata files (.json)

AFTER GENERATION:
  SWE-smith rmtree executed: repo deleted = True
  Restoration from golden:  SUCCESS
  Restored HEAD == golden:  True (75284f9593dfb929cadd900aff9e35e7c7aec54b)
  Restored git status:      CLEAN
  Restored state hash ==:   True (28921257f5b7e4b1fef370603a89fa3f89fcb76e0ac564072019c5e0d0d39922)

CANDIDATE ARTIFACT SURVIVAL:
  Artifacts surviving:      18 / 18 (100%)
  Survival Status:          PASS
OVERALL GATE 3 RESULT:      PASS
```

All test artifacts were immediately cleaned up and the repository state was verified 100% clean.

---

## GATE 4 — Treatment Independence Audit

The ephemeral golden-copy wrapper was audited for treatment independence:
1. **Timing of Execution**: The golden-copy lifecycle runs strictly during Phase D1 candidate generation and Phase D2 offline validation, well before treatment assignment occurs.
2. **Arm Invariance**: In Phase D4 / Primary Trials, the repository environment provisioning logic is identical for both `loop_retry` and `loop_verify`. The restoration operation copies the clean baseline state with zero branch conditions dependent on `treatment_arm`, `verifier_output`, or `agent_output`.
3. **Purity**: Candidate task units are serialized to static YAML before calibration or primary trials begin. No treatment keys (`treatment_success`, `loop_retry_outcome`, etc.) can leak into candidate definitions.

---

## GATE 5 — Protocol Amendment Matrix

| Amendment | Original Rule | Proposed New Rule | Reason | Scientific Impact | Requires Prereg Hash? |
|---|---|---|---|---|---|
| **1. Seed Reconciliation** | Protocol 02 §4 specified placeholder `PRNG_SEED_REPO = 10001` | Formally reconcile `PRNG_SEED_REPO = 61022` per Protocol 05 hierarchy | Eliminate draft contradiction; enforce `(MASTER_SEED + 101) % 100000` | Zero causal impact; guarantees deterministic seed derivation | Yes |
| **2. Repository Exclusion** | Protocol 02 §3 registered `marshmallow` and `sqlfluff` as `ELIGIBLE` | Reclassify `marshmallow` and `sqlfluff` as `EXCLUDED (BASELINE_FAIL / UNPINNED_DEPENDENCY)` | Both fail clean offline baseline unit tests; lack lockfiles; unpinned PyPI install violates Rules G5/G6 | Enforces fail-closed reproducibility and supply-chain integrity | Yes |
| **3. Single-Repository Candidate Pool** | Candidate pool sampled across 3 repositories in 3 batches | Sample all $K=30$ candidates exclusively from `mewwts__addict.75284f95` | `mewwts__addict` is the only eligible repository remaining | **FATAL DEFECT**: Destroys repository diversity; fails $K=30$ capacity ($K \le 7$ under Protocol 12 §1) | Yes |
| **4. SWE-smith Lifecycle Preservation** | Direct script invocation of SWE-smith | Ephemeral working copy wrapper: restore from `<repo>.golden` post-`rmtree` | SWE-smith unconditionally deletes checkout directory at `generate.py:L184` | Enables offline validation on restored repo without modifying SWE-smith | Yes |

---

## GATE 6 — Inference Scope & Generalizability Limits

If EXP-LOOP-003 were executed exclusively on `mewwts__addict.75284f95`:
1. **Severely Restricted Target Population**: Findings would characterize only the performance of LLM coding agents on small, single-file dictionary data structures under synthetic LibCST AST mutations.
2. **Invalidated Broad Research Claim**: The original research question (*"Does verification improve multi-turn agent repair performance across software engineering tasks?"*) could NOT be claimed. It would have to be qualified as:
   > *"On small Python dictionary data-structure tasks with dense unit tests, comparing loop_verify to loop_retry..."*
3. **Clustered Variance Risk**: With all tasks concentrated in `addict.py` (and primarily in `__init__`), observations are highly correlated. The effective sample size $N_{\text{eff}}$ would collapse from 30 to $\le 7$, rendering statistical tests underpowered and invalid.

---

## GATE 7 — Final Authorization Checklist

| Authorization Requirement | Status | Evidence / Notes |
|---|---|---|
| 1. Repository-pool amendment is formally defensible | **FAIL** | Excludes 2 repos cleanly, but single-repo pool cannot support $K=30$ |
| 2. $K=30$ capacity $\ge 30$ | **FAIL** | Upper bound is 7 under Protocol 12 §1, 20 under raw (entity, rule) |
| 3. Candidate independence deterministically enforceable | **FAIL** | Violates Protocol 12 §1 (requires multiple tasks in `__init__`) |
| 4. Golden-copy lifecycle test passes | **PASS** | Verified: commit clean, hash matches, checkout restored |
| 5. Generated artifacts survive repository restoration | **PASS** | 100% of artifacts survive in `logs/bug_gen` outside repo |
| 6. Treatment independence is preserved | **PASS** | Zero feedback leakage; restoration is treatment-invariant |
| 7. All amendments documented | **PASS** | Complete audit trail in `docs/DEVIATIONS.md` and reports |
| 8. Protocol files cryptographically sealed | **PENDING** | Protocol cannot be sealed while design is rejected |
| 9. No candidate has entered the primary pool | **PASS** | Zero candidates generated; pool count is 0 |
| 10. Fresh D0 rerun required before D1 | **HOLD** | D0 cannot pass until candidate pool design is resolved |

---

## Final Status Line

```text
=============================================================================
FINAL AUDIT STATUS: BLOCKED — K=30 CAPACITY INSUFFICIENT
=============================================================================
```
