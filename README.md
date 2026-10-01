# LERM: Loop Engineering Research Machine

<p align="center">
  <img src="docs/diagrams/01_system_architecture_3d.svg" alt="LERM System Architecture" width="100%" />
</p>

<p align="center">
  <strong>Causal inference, pre-registered experimentation, and adversarial verification for autonomous software engineering loops.</strong>
</p>

<p align="center">
  <a href="#test-suite--benchmarks"><img src="https://img.shields.io/badge/tests-88%20passed-10b981.svg?style=flat-square" alt="Tests" /></a>
  <a href="#adversarial-audit"><img src="https://img.shields.io/badge/adversarial%20audit-20%2F20%20passed-38bdf8.svg?style=flat-square" alt="Adversarial Audit" /></a>
  <a href="#phase-c-protocol-freeze"><img src="https://img.shields.io/badge/protocol-Phase%20C%20Frozen-8b5cf6.svg?style=flat-square" alt="Protocol" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License" /></a>
  <a href="#prerequisites"><img src="https://img.shields.io/badge/python-3.9%2B-blue.svg?style=flat-square" alt="Python Version" /></a>
  <a href="#cost"><img src="https://img.shields.io/badge/cloud%20spend-%240.00-emerald.svg?style=flat-square" alt="Zero Cost" /></a>
</p>

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Why Does This Exist?](#2-why-does-this-exist)
3. [Research Questions](#3-research-questions)
4. [System Architecture](#4-system-architecture)
5. [Visual Architecture Diagrams](#5-visual-architecture-diagrams)
6. [Core Modules — What Each File Does](#6-core-modules--what-each-file-does)
7. [Protocol Documents (16 Specifications)](#7-protocol-documents-16-specifications)
8. [Test Suite & Benchmarks](#8-test-suite--benchmarks)
9. [Verified Experimental Findings & Negative Results](#9-verified-experimental-findings--negative-results)
10. [Design Decisions (6 Canonical Decisions)](#10-design-decisions-6-canonical-decisions)
11. [Protocol Deviations (10 Documented)](#11-protocol-deviations-10-documented)
12. [Data & Artifacts](#12-data--artifacts)
13. [What Was Done (Development Timeline)](#13-what-was-done-development-timeline)
14. [What Was NOT Done (Planned Work)](#14-what-was-not-done-planned-work)
15. [Reproducibility & Quick Start](#15-reproducibility--quick-start)
16. [Project Structure](#16-project-structure)
17. [Research Roadmap](#17-research-roadmap)
18. [License & Citation](#18-license--citation)

---

## 1. What Is This Project?

**LERM (Loop Engineering Research Machine)** is an open-source scientific research machine that tests whether autonomous coding agent "loops" (verify-repair cycles) actually work — or whether published improvements are statistical artifacts of confounded experiments.

It treats the agent scaffold as an **experimental intervention** within a **randomized controlled trial (RCT)** framework, with:
- **Cryptographic pre-registration** (hypotheses sealed before execution)
- **Fail-closed data firewalls** (historical task contamination blocked mechanically)
- **Adversarial skeptic auditor** (5-attack vector suite from an independent model family)
- **Compute-matched comparison arms** (identical turn, token, and wallclock budgets)
- **Unbiased pass^k reliability metric** (not the inflated pass@k used in most papers)

The entire system runs at **₹0 / $0 cloud cost** using local Ollama inference and free-tier OpenRouter APIs.

---

## 2. Why Does This Exist?

Autonomous software engineering agents are frequently claimed to be "dramatically improved" by in-loop verification, multi-agent debate, or automated retry. However, the majority of published results suffer from severe methodological confounds:

| Confound | What Happens | How LERM Prevents It |
|---|---|---|
| **Compute Asymmetry** | Treatment arm gets 2×–5× more tokens/time than control | Strict matched budgets (3 turns, 16K tokens, 120s wallclock) |
| **Benchmark Leakage** | Public benchmark tasks are in model pre-training data | Procedural AST mutations on fresh repositories (SWE-smith) |
| **Stochastic Cherry-Picking** | Authors report pass@k (any 1 of k worked) as success | Unbiased pass^k estimator (ALL k must succeed) |
| **Ungrounded Verifiers** | Verifiers game test fixtures, declare false accepts | Independent container-isolated evaluator; agent never sees tests |
| **Post-Hoc Task Selection** | Tasks pruned after inspecting model performance | Pre-registered task manifests; SHA-256 sealed before execution |

---

## 3. Research Questions

| ID | Research Question | Status |
|---|---|---|
| **RQ1** | Does in-loop verification and repair (`loop_verify`) yield a statistically significant improvement in pass^k verified success over a compute-matched naive retry baseline (`loop_retry`) under identical turn, token, and wallclock caps? | `OPEN` — awaiting EXP-LOOP-003 primary trial |
| **RQ2** | How does the verifier False Accept Rate (FAR) degrade multi-turn repair trajectories on long-horizon software engineering tasks? | `OPEN` |
| **RQ3** | Can an adversarial auditor (L0) from an independent model family refute spurious empirical findings before they enter the research knowledge base? | `VERIFIED` — L0 skeptic refuted 3 of 3 flawed findings |

---

## 4. System Architecture

LERM is structured into **four distinct planes** separated by strict causal firewalls:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 4: SCIENTIFIC GOVERNANCE & ADVERSARIAL SKEPTIC (L0)                   │
│  • Skeptic 5-Attack Suite • Knowledge Base (KB) • Spend & Drift Guardrails  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Pre-reg Verification & Skeptic Review
┌──────────────────────────────────────▼──────────────────────────────────────┐
│  LAYER 3: CAUSAL CONTROL PLANE & DATA FIREWALL                              │
│  • Pre-registration Hasher • Fail-Closed Firewall • Deterministic Controller │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Matched Arms Dispatch & Isolation
┌──────────────────────────────────────▼──────────────────────────────────────┐
│  LAYER 2: L1 TRACE TELEMETRY & CONFOUND BALANCER                             │
│  • Unmerged 3-Outcome Traces • 10-Confound Checklist • Pass^k Estimator     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Ephemeral Container Mounts & Signals
┌──────────────────────────────────────▼──────────────────────────────────────┐
│  LAYER 1: EXECUTION PLANE & CONTAINER SANDBOX (ADR-0001)                     │
│  • Ephemeral Docker Sandbox • Read-Only Pytest Evaluator • Resource Manager │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Governing Principle:**
> `TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT`

For the complete technical specification, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 5. Visual Architecture Diagrams

All diagrams are located in `docs/diagrams/` as production SVG files:

| Diagram | Description | File |
|---|---|---|
| System Architecture | 4-layer separated plane overview | [`01_system_architecture_3d.svg`](docs/diagrams/01_system_architecture_3d.svg) |
| Data & Control Flow | End-to-end experiment lifecycle from pre-reg to KB settlement | [`02_data_control_flow_3d.svg`](docs/diagrams/02_data_control_flow_3d.svg) |
| Agent Loop Comparison | Matched-budget `loop_retry` vs `loop_verify` (3 turns, 16K tokens, 120s) | [`03_agent_loop_3d.svg`](docs/diagrams/03_agent_loop_3d.svg) |
| Verification Chain | 8-stage candidate verification: Baseline → Mutation → GT Fail → Repair → GT Pass → Reset Hash | [`04_verification_eval_3d.svg`](docs/diagrams/04_verification_eval_3d.svg) |
| Failure & Recovery | Non-merged 3-outcome taxonomy (verified_success, infra_failure, model_failure) with OOM eviction | [`05_failure_recovery_flow_3d.svg`](docs/diagrams/05_failure_recovery_flow_3d.svg) |
| Roadmap & Vision | 5-phase progression from control plane to autonomous AI scientist | [`06_roadmap_vision_3d.svg`](docs/diagrams/06_roadmap_vision_3d.svg) |

---

## 6. Core Modules — What Each File Does

### `lerm/` — Core Package (21 modules)

| Module | Lines | Purpose |
|---|---|---|
| [`stats.py`](lerm/stats.py) | 301 | **Statistical core.** Unbiased pass^k (combinatorial C(c,k)/C(n,k)) and pass@k (Chen et al.) estimators, paired bootstrap CI (resamples tasks not runs), O'Brien-Fleming sequential stopping boundaries, power analysis, Wilson score & Clopper-Pearson intervals, calibration admission gates. |
| [`skeptic.py`](lerm/skeptic.py) | 218 | **Adversarial Skeptic (L0).** 5-attack suite: (1) replication with new seeds, (2) confound search, (3) shortcut/reward-hack hunt, (4) alternative explanation, (5) noise check against pre-registered CI threshold. Hard-enforces different model family at construction. |
| [`firewall.py`](lerm/firewall.py) | 230 | **Fail-closed data firewall.** Quarantines historical holdouts (HOLDOUT-001–004) by task ID AND fixture content SHA-256 hash. Blocks string booleans, missing flags, metadata tampering, and copied fixture artifacts. |
| [`candidate_pool.py`](lerm/candidate_pool.py) | 266 | **Candidate pool manager & rejection taxonomy.** 9-gate admission pipeline: firewall → schema → provenance → treatment purity → hash verification → mutation dedup → diff dedup → config dedup → 8-step chain verification. 16 rejection categories. |
| [`candidate_schema.py`](lerm/candidate_schema.py) | 155 | **Immutable candidate task unit schema.** 20 typed fields (task_id format, git SHA validation, mutation rule allowlist, SHA-256 hash format, provenance requirements). Frozen at Schema v1.0.0. |
| [`calibration.py`](lerm/calibration.py) | 155 | **Phase D difficulty calibration.** Two-stage sequential screening (N₁=10 Stage 1, N=20 Stage 2), guardband admission rule (0.35 ≤ p̂ ≤ 0.65), Wilson CI intersection with [0.30, 0.70], manifest YAML generator. |
| [`confounds.py`](lerm/confounds.py) | ~135 | **10-dimension mechanical confound checklist.** Validates: equal wallclock, equal tokens, equal attempts, equal cost, same model version, no model drift, comparable task order, same seed policy, same task set, no human intervention. |
| [`trace.py`](lerm/trace.py) | ~225 | **Immutable trace store.** Append-only JSONL. Non-merged 3-field outcome taxonomy: `verified_success`, `infra_failure`, `model_failure`. Tracks LERM framework overhead ratio (≤10%). |
| [`prereg.py`](lerm/prereg.py) | ~145 | **Cryptographic pre-registration.** SHA-256 sealed YAML manifests. `prereg.verify()` asserts git-tracked files unmodified post-hoc. |
| [`kb.py`](lerm/kb.py) | ~215 | **Knowledge Base & settlement.** Three-valued verdicts: `SUPPORTED`, `REFUTED`, `UNCERTAIN`. Rejects hedging prose ("promising", "suggests", "trend"). Requires explicit `unexplained` field. |
| [`controller.py`](lerm/controller.py) | ~95 | **Deterministic loop controller.** Manages `loop_retry` (Arm A) vs `loop_verify` (Arm B) under matched budgets: max 3 turns, 16K tokens, 120s wallclock. |
| [`evaluator.py`](lerm/evaluator.py) | ~95 | **Independent evaluator.** Runs pytest in ephemeral container. Agent's self-reported claim is NEVER ingested as ground truth. |
| [`resource.py`](lerm/resource.py) | ~100 | **Hardware resource manager.** Monitors physical RAM via Windows API. Proactively evicts Ollama models (keep_alive=0) when RAM < 2GB to prevent OOM thrashing on 16GB hardware. |
| [`guardrails.py`](lerm/guardrails.py) | ~140 | **Spend & drift guardrails.** Three-tier spend ceiling ($25/hr, $200/day, $800/week). Kill-switch via `state/KILL` file. Canary prompt monitoring for silent API-side model weight updates. |
| [`digest.py`](lerm/digest.py) | ~95 | **Daily/weekly digest generator.** Summarizes trace telemetry into human-readable markdown reports. |
| [`ledger.py`](lerm/ledger.py) | ~65 | **Append-only experiment ledger.** JSONL-backed immutable record of all experiment events. |
| [`regression.py`](lerm/regression.py) | ~95 | **Regression detection.** Compares current results against prior baselines to detect performance degradation. |
| [`repairability.py`](lerm/repairability.py) | ~130 | **Treatment-independent repairability classifier.** Categories: `REPAIRABLE`, `UNREPAIRABLE`, `INFRASTRUCTURE`, `AMBIGUOUS`, `EVALUATOR_FAILURE`. Zero reliance on loop outcomes. |
| [`trace_purity.py`](lerm/trace_purity.py) | ~50 | **Calibration trace purity auditor.** Verifies zero loop feedback / verifier diagnostics leaked into calibration traces. |
| [`checkpoint.py`](lerm/checkpoint.py) | ~95 | **Experiment checkpoint manager.** Persists and restores in-flight experiment state for crash recovery. |

### `lerm/adapters/` — Execution Plane Adapters

| Module | Lines | Purpose |
|---|---|---|
| [`openhands.py`](lerm/adapters/openhands.py) | 266 | **OpenHands agent-server adapter.** HTTP client (stdlib urllib only) for OpenHands v1 & legacy v0 APIs. Conversation lifecycle: start → poll → events → sandbox. OmniRoute model plane integration with traced completions. Rate-limited retry with exponential backoff. |

---

## 7. Protocol Documents (16 Specifications)

All protocols are in `docs/protocol/` and cryptographically hashed in the Phase C Audit Report:

| # | Protocol | File | What It Defines |
|---|---|---|---|
| 01 | Candidate Schema | [`01_candidate_schema.md`](docs/protocol/01_candidate_schema.md) | 20-field immutable task unit: types, formats, validation rules |
| 02 | Repository Sampling | [`02_repository_sampling_policy.md`](docs/protocol/02_repository_sampling_policy.md) | Deterministic repo selection (PRNG seeded), baseline pass requirement |
| 03 | Mutation Policy | [`03_mutation_policy.md`](docs/protocol/03_mutation_policy.md) | 5 allowed AST mutation operators, prohibited operators, compound mutations |
| 04 | Generator Config | [`04_candidate_generation_config.md`](docs/protocol/04_candidate_generation_config.md) | SWE-smith invocation parameters, deterministic RNG seeding |
| 05 | Random Seed Policy | [`05_random_seed_policy.md`](docs/protocol/05_random_seed_policy.md) | Master seed hierarchy (MASTER_SEED=20260921), derived subsystem seeds |
| 06 | Calibration Protocol | [`06_calibration_protocol.md`](docs/protocol/06_calibration_protocol.md) | Two-stage sequential screening (N₁=10, N=20), guardband admission |
| 07 | Repairability Protocol | [`07_repairability_protocol.md`](docs/protocol/07_repairability_protocol.md) | Treatment-independent classification, reference patch verification |
| 08 | Ground Truth Protocol | [`08_ground_truth_protocol.md`](docs/protocol/08_ground_truth_protocol.md) | Container-isolated pytest execution, zero agent self-report trust |
| 09 | Rejection Taxonomy | [`09_candidate_rejection_taxonomy.md`](docs/protocol/09_candidate_rejection_taxonomy.md) | 16 deterministic rejection categories with mandatory logging |
| 10 | Manifest Format | [`10_candidate_manifest_format.md`](docs/protocol/10_candidate_manifest_format.md) | Frozen YAML manifest structure, atomic validation |
| 11 | Provenance Specification | [`11_provenance_specification.md`](docs/protocol/11_provenance_specification.md) | Required provenance keys: generator_version, config_hash, timestamp |
| 12 | Independence Specification | [`12_independence_specification.md`](docs/protocol/12_independence_specification.md) | One task per function, triple dedup (mutation_id, diff hash, config tuple) |
| 13 | Leakage Audit | [`13_information_leakage_audit.md`](docs/protocol/13_information_leakage_audit.md) | Forbidden treatment keys, zero generator→trace dependencies |
| 14 | Adversarial Test Suite | [`14_adversarial_test_suite.md`](docs/protocol/14_adversarial_test_suite.md) | 20 attack vectors specified for candidate pool integrity |
| 15 | Reproducibility Tests | [`15_reproducibility_test_results.md`](docs/protocol/15_reproducibility_test_results.md) | Bit-for-bit determinism across 3 configurations |
| 16 | Calibration OC Analysis | [`16_calibration_operating_characteristics.md`](docs/protocol/16_calibration_operating_characteristics.md) | Exact binomial admission probabilities across true-p values |

---

## 8. Test Suite & Benchmarks

**Total: 88 tests, all passing** (verified 2026-10-01, Python 3.14, `pytest 9.1.1`, 4.79s)

### Test Files

| File | Tests | What It Validates |
|---|---|---|
| [`tests/test_core.py`](tests/test_core.py) | 27 | Core statistics (pass^k, pass@k, bootstrap CI, power analysis, Fisher exact p, O'Brien-Fleming boundaries), pre-registration seal/verify, Knowledge Base settlement (hedging rejection, unexplained field), verifier quality FAR/FRR, trace 3-outcome taxonomy, confound checklist, regression detection, controller budget enforcement, Wilson score interval, calibration sample size |
| [`tests/test_firewall.py`](tests/test_firewall.py) | 13 | Data firewall: historical task rejection (by ID and fixture hash), metadata tampering detection, string boolean rejection, missing flag rejection, copied fixture detection, fresh candidate admission, trace dataset contamination blocking |
| [`tests/test_candidate_adversarial.py`](tests/test_candidate_adversarial.py) | 20 | **Full adversarial audit** — 20 distinct attack vectors against the candidate pool (see §8.1 below) |
| [`tests/test_repairability.py`](tests/test_repairability.py) | 7 | Repairability classifier: repairable, unrepairable (no patch, no signal), infrastructure failure, evaluator syntax failure, ambiguous/flaky, timeout |
| [`tests/test_skeptic_planted.py`](tests/test_skeptic_planted.py) | 7 | Planted-finding skeptic attacks: confounded finding killed, shortcut finding killed, noise finding killed, honest finding survives, same-model-family refused, seed policy flagged, fixture reset mismatch flagged |
| [`tests/test_calibration_stage2.py`](tests/test_calibration_stage2.py) | 14 | Stage 2 precision evaluation: admission gate (7 ≤ X ≤ 13), Wilson CI intersection, edge cases (0/20, 20/20, 7/20, 13/20), metrics computation, trace purity |

### 8.1 Adversarial Test Suite (20 Attack Vectors)

Every vector validates fail-closed rejection of invalid, poisoned, or contaminated candidates:

```
 #  Attack Vector                                    Expected Rejection
 1  Historical task injected into calibration         HISTORICAL_FIREWALL_BREACH
 2  Historical task injected into primary             HISTORICAL_FIREWALL_BREACH
 3  Fresh task with fake provenance                   PROVENANCE_TAMPERED
 4  Fresh task with missing provenance                CandidateValidationError
 5  Fresh task with altered provenance                PROVENANCE_TAMPERED
 6  Candidate copied from historical fixture          FirewallViolation
 7  Candidate with one-byte source perturbation       HASH_MISMATCH
 8  Duplicate mutation                                DUPLICATE_MUTATION
 9  Same mutation under different ID                  DUPLICATE_DIFF
10  Treatment-success leaked into metadata            TREATMENT_LEAKAGE
11  Calibration result leaked into generator state    TREATMENT_LEAKAGE
12  Candidate missing mutation ID                     CandidateValidationError
13  Candidate mismatched repository/commit            CandidateValidationError
14  Candidate mismatched content hash                 CandidateValidationError
15  Candidate baseline already fails                  BASELINE_FAILURE
16  Candidate mutation produces no failure            MUTATION_NO_EFFECT
17  Candidate failure is infrastructure-only          INFRASTRUCTURE_FAILURE
18  Reference repair does not restore PASS            REFERENCE_REPAIR_FAILURE
19  Candidate reset hash differs                      RESET_FAILURE
20  Candidate generated with same seed twice          DUPLICATE_CONFIG
```

### 8.2 Reproducibility Benchmark

100% bit-for-bit deterministic SWE-smith bug generation verified across 3 independent configurations:
- **CONFIG_A** (`mewwts__addict`, seed=42): 2 files identical
- **CONFIG_B** (`mewwts__addict`, seed=101): 6 files identical
- **CONFIG_C** (`mewwts__addict`, seed=999): 18 files identical

Run: `python verify_3_configs_reproducibility.py`

### 8.3 Statistical Benchmarks

- **Power Analysis**: At N=7 tasks (k=5, p₀=0.50^5=0.03125, α=0.05), power to detect MDE=0.20 is 18.62%. N≥44 required for 80% power at MDE=0.20.
- **Calibration Operating Characteristics**: Guardband rule (0.35 ≤ p̂ ≤ 0.65) at true p=0.50 yields P(Admit)=0.8770; at true p=0.05 yields P(Admit)=0.0000 (zero floor leakage).
- **Wilson Score vs Wald**: Wilson score CI is preferred because Wald severely under-covers near boundaries.

---

## 9. Verified Experimental Findings & Negative Results

LERM mandates public documentation of **all** results including negative ones. This is central to scientific integrity.

### 9.1 Finding LE-0001 (Offline Pilot Simulation)
- **File**: [`findings/LE-0001.yaml`](findings/LE-0001.yaml)
- **Hypothesis**: Independent verification in the loop improves pass^5 verified success more than equal-compute retries.
- **Observed Effect**: +0.175 [+0.067, +0.282], FAR=0.051
- **Skeptic Verdict**: `UNCERTAIN` — survived confound search, shortcut hunt, and noise check; flagged `NEEDS_EXECUTION` for replication and alternative explanation.
- **Model**: `qwen/qwen3-coder-480b` (simulated), N=1200 runs, 60 tasks

### 9.2 FINDING-EXP-LOOP-001 (Live Pilot — Refuted)
- **File**: [`negative_results/FINDING-EXP-LOOP-001.yaml`](negative_results/FINDING-EXP-LOOP-001.yaml)
- **Status**: `REFUTED`
- **Reason**: Confound search KILLED (wallclock 33% imbalanced, tokens 9% imbalanced). Noise check KILLED (CI includes zero at n_tasks=4).
- **Model**: `inkling-small:free`

### 9.3 FINDING-EXP-LOOP-002 (Live Pilot — Refuted, Ceiling Effect)
- **File**: [`negative_results/FINDING-EXP-LOOP-002.yaml`](negative_results/FINDING-EXP-LOOP-002.yaml)
- **Status**: `REFUTED`
- **Finding**: **Zero treatment variance.** Out of 79 valid trials, 100% of successful trials solved on Turn 1 before retry or verification mechanics could engage.
- **Root Cause**: Hand-crafted holdout tasks were too easy for the model, collapsing multi-turn variance.
- **Remediation**: Designed the Phase C Candidate Generation and Sequential Calibration Protocol to enforce 0.35 ≤ p̂ ≤ 0.65 single-shot baseline difficulty.

### 9.4 NEG-LIVE-0001 (Pipeline Integrity — Refuted)
- **File**: [`negative_results/NEG-LIVE-0001.yaml`](negative_results/NEG-LIVE-0001.yaml)
- **Status**: `REFUTED`
- **Finding**: 6 pipeline defects discovered: (D1) hardcoded demo data in regression_result, (D2) model emitted raw JSON without ActionEvent, (D3) HOLDOUT-001 passed on untouched fixtures, (D4) checkers missing exit code 2, (D5) trace timing 52μs apart, (D6) shortcut_pilot mock placeholder.
- **Remediation**: All 6 defects catalogued and fixed. Trust pipeline rebuilt from scratch.

---

## 10. Design Decisions (6 Canonical Decisions)

All decisions are recorded in [`docs/DECISIONS.md`](docs/DECISIONS.md):

| ID | Question | Resolution |
|---|---|---|
| **DECISION-0001** | Governing protocol version | Adopted LERM Protocol v2 (SHA-256 sealed) |
| **DECISION-0002** | EXP-LOOP-003 candidate pool scope | Phase D-partial on `addict` only (K_max=14). `marshmallow` and `sqlfluff` blocked by offline dependency failures. |
| **DECISION-0003** | Execution mechanism parity | Raw completion calibration sets upper bound on intrinsic difficulty; EXP-LOOP-003 must match pathways. |
| **DECISION-0004** | Raw completion vs OpenHands calibration | Raw completion as cheap screen; OpenHands confirmation gate mandatory before primary admission. `qwen2.5-coder:1.5b` cannot execute OpenHands tool actions (0/20 trials). |
| **DECISION-0005** | Agent-under-test model | `openrouter/thinkingmachines/inkling-small:free` confirmed. `qwen2.5-coder:1.5b/3b` disqualified (cannot invoke bash/editor tools in OpenHands). |
| **DECISION-0006** | Ceiling effect resolution | In-agent bash testing is valid capability. Candidates require compound/multi-mutation. Calibration throttled ≤15 trials/day for ₹0 budget preservation. |

---

## 11. Protocol Deviations (10 Documented)

All deviations are recorded in [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md) with evidence:

1. `n_reruns >= 2k`, not `n_reruns == k` (at n=k=5, task-level CI blows up)
2. Bootstrap resamples tasks, not runs (tasks are the unit of generalisation)
3. DuckDB is optional (JSONL is source of truth; SQLite fallback)
4. Skeptic attacks 1 & 4 return `NEEDS_EXECUTION`, never `PASS` (pre-execution honesty)
5. Spend cap default deliberately low ($3/h, $40/day)
6. Skeptic model family check is a hard error at construction
7. PRNG_SEED_REPO reconciled to 61022 (from master seed hierarchy)
8. Repository pool restricted to `addict` only (DECISION-0002)
9. Golden-copy preservation wrapper for SWE-smith `shutil.rmtree` behavior
10. Autonomous tool interaction & compound mutation calibration policy (DECISION-0006)

---

## 12. Data & Artifacts

### Preregistrations (Sealed Before Execution)
| File | Experiment |
|---|---|
| [`preregistrations/LE-0001.yaml`](preregistrations/LE-0001.yaml) | Offline pilot simulation |
| [`preregistrations/EXP-LOOP-001.yaml`](preregistrations/EXP-LOOP-001.yaml) | Live pilot with inkling-small |
| [`preregistrations/EXP-LOOP-002.yaml`](preregistrations/EXP-LOOP-002.yaml) | Live pilot with wallclock matching |

### Holdout Tasks
| File | Description |
|---|---|
| [`holdout/tasks/HOLDOUT-001.yaml`](holdout/tasks/HOLDOUT-001.yaml) – [`HOLDOUT-004.yaml`](holdout/tasks/HOLDOUT-004.yaml) | Historical holdout tasks from EXP-LOOP-002 (quarantined in firewall) |
| [`holdout/tasks/_schema.yaml`](holdout/tasks/_schema.yaml) | Holdout task schema definition |

### Phase D Calibration Data
| File | Description |
|---|---|
| `data/phase-d/candidates.jsonl` | 7 generated candidate tasks (Cohort 1) |
| `data/phase-d/compound_candidates.jsonl` | Compound multi-mutation candidates |
| `data/phase-d/candidates_manifest.yaml` | Frozen candidate manifest |
| `data/phase-d/calibration_traces*.jsonl` | Calibration trace records |
| `data/phase-d/calibration_summary*.json` | Summary metrics for calibration runs |
| `data/phase-d/admitted_primary_manifest.yaml` | Tasks admitted to primary pool |

### Reports
| File | Description |
|---|---|
| [`reports/PHASE_C_AUDIT_REPORT.md`](reports/PHASE_C_AUDIT_REPORT.md) | **Phase C Protocol Freeze** — 20-gate binary checklist, 26 cryptographically hashed artifacts, all gates PASS |
| [`reports/P0_LIVE_VERIFICATION.md`](reports/P0_LIVE_VERIFICATION.md) | P0 live pipeline verification report |
| [`reports/GITHUB_PUBLICATION_REPORT.md`](reports/GITHUB_PUBLICATION_REPORT.md) | Publication audit |
| `reports/phase-d/` | Phase D preflight, remediation design, reconciliation, dependency audit, final report |

---

## 13. What Was Done (Development Timeline)

### Phase 0/1: Control Plane Foundation
- Built the full 4-layer architecture from scratch
- Implemented cryptographic pre-registration with SHA-256 sealing
- Implemented fail-closed data firewall with historical task quarantine
- Built adversarial skeptic (L0) with 5-attack vector suite
- Implemented 10-dimension mechanical confound checklist
- Built unbiased pass^k estimator (combinatorial, not naive power)
- Built paired bootstrap CI (task-level, not run-level)
- Implemented O'Brien-Fleming sequential stopping boundaries
- Built hardware resource manager with Ollama OOM eviction
- Built Knowledge Base with three-valued verdicts and hedging rejection
- Built spend guardrails with kill-switch

### Phase B: Pilot Trials (EXP-LOOP-001, EXP-LOOP-002)
- Ran 40 trials (EXP-LOOP-001) → REFUTED (confounded wallclock & tokens)
- Ran 79 trials (EXP-LOOP-002) → REFUTED (ceiling effect, 100% Turn 1 solve)
- Discovered pipeline integrity defects (NEG-LIVE-0001) → 6 defects catalogued

### Phase C: Protocol Freeze & Adversarial Audit
- Froze 16 protocol specifications
- Built candidate schema (20-field immutable CandidateTaskUnit)
- Built candidate pool manager with 9-gate admission pipeline
- Built 20-vector adversarial test suite → 20/20 PASS
- Verified SWE-smith bit-for-bit reproducibility across 3 configs
- Computed calibration operating characteristics (exact binomial)
- All 20 Phase C gate conditions PASS
- Cryptographically hashed all 26 protocol artifacts

### Phase D: Candidate Generation & Calibration (In Progress)
- Generated Cohort 1 candidates (7 tasks) from `mewwts__addict`
- Discovered marshmallow/sqlfluff offline dependency failures
- Ran raw completion calibration → discovered ceiling effect with OpenHands tool access
- Designed compound mutation strategy (DECISION-0006)
- Generated compound candidate pairs
- Built Phase D calibration evaluation module
- Built OpenHands adapter (stdlib-only HTTP, v1+v0 API support)
- Probed model capabilities: `qwen2.5-coder:1.5b` disqualified (0 tool actions), `inkling-small:free` confirmed
- Built Stage 2 calibration tests (14 tests)

### Scripts Built
| Script | Purpose |
|---|---|
| [`scripts/preflight.py`](scripts/preflight.py) | P0 environment preflight checks |
| [`scripts/demo_offline.py`](scripts/demo_offline.py) | Full offline demo: prereg → traces → skeptic → KB → digest |
| [`scripts/validate_tasks.py`](scripts/validate_tasks.py) | Holdout task schema validation |
| [`scripts/run_causal_experiment.py`](scripts/run_causal_experiment.py) | Primary causal experiment runner (ready for EXP-LOOP-003) |
| [`scripts/run_live_lerm.py`](scripts/run_live_lerm.py) | Live LERM pipeline runner |
| [`scripts/generate_phase_d_candidates.py`](scripts/generate_phase_d_candidates.py) | Phase D candidate generation |
| [`scripts/generate_compound_candidates.py`](scripts/generate_compound_candidates.py) | Compound multi-mutation candidate generation |
| [`scripts/run_phase_d_calibration.py`](scripts/run_phase_d_calibration.py) | Phase D calibration (raw completion) |
| [`scripts/run_phase_d_calibration_openhands.py`](scripts/run_phase_d_calibration_openhands.py) | Phase D calibration (OpenHands) |
| [`scripts/verify_broken_fixtures.py`](scripts/verify_broken_fixtures.py) | Fixture integrity verification |
| [`scripts/verify_phase_a.py`](scripts/verify_phase_a.py) | Phase A verification |
| [`scripts/audit_phase_b.py`](scripts/audit_phase_b.py) | Phase B audit |

---

## 14. What Was NOT Done (Planned Work)

| Item | Status | Why |
|---|---|---|
| **EXP-LOOP-003 Primary Causal Trial** | `PLANNED` | Awaiting Phase D candidate pool completion. Pre-registered; script ready (`scripts/run_causal_experiment.py`). |
| **Phase D Full Pool (K=30 across 3 repos)** | `BLOCKED` | `marshmallow` and `sqlfluff` have unpinned floating dependencies that fail pytest offline. Currently K_max=14 from `addict` only. |
| **Multi-Cloud Ray Execution** | `VISION` | Phase 4/5 roadmap item. Requires SkyPilot cluster provisioning. |
| **Autonomous 24/7 Research Loop** | `VISION` | Self-directed hypothesis generation, auto-pre-registration, paper draft synthesis. |
| **LaTeX Manuscript Synthesis** | `VISION` | Automated paper generation from settled KB records. |
| **DVC Integration** | `DEFERRED` | Large trace files tracked via git-ignored directories; DVC or release assets planned for scale. |

---

## 15. Reproducibility & Quick Start

### Prerequisites
- **Python 3.9+** (tested on Python 3.14, Windows 11 / WSL2)
- **Docker Desktop / Engine** (required for containerized evaluation)
- **Git**
- **(Optional)** [Ollama](https://ollama.ai/) for local zero-cost inference

### Installation
```bash
# Clone the repository
git clone https://github.com/Nia00-glitch/lerm.git
cd lerm

# Install package and core dependencies in editable mode
pip install -e .

# (Optional) Install dev dependencies for analytics
pip install -e ".[dev]"
```

### Configuration
```bash
# Copy example environment configuration
cp .env.example .env

# Edit .env with your local or remote LLM endpoint
# Works with local Ollama (http://127.0.0.1:11434) at zero monetary cost
# Or use OpenRouter free-tier models
```

### Verification & Selftest
```bash
# 1. Run complete test suite (88 tests)
pytest tests/ -v

# 2. Validate holdout tasks against schema
python scripts/validate_tasks.py

# 3. Verify SWE-smith bit-for-bit determinism across 3 configurations
python verify_3_configs_reproducibility.py

# 4. Verify pre-registration hash integrity
python -c "from lerm.prereg import verify; print(verify('preregistrations/EXP-LOOP-002.yaml'))"

# 5. Run full offline demo (prereg → traces → skeptic → KB → digest)
python scripts/demo_offline.py

# 6. Run P0 preflight environment checks
python scripts/preflight.py
```

### Makefile Targets
```bash
make preflight   # P0 gate — environment health check
make selftest    # P5 acceptance: skeptic must kill planted findings
make demo        # Full offline end-to-end demo
make lock        # Lock pip dependencies
make clean       # Clean runtime artifacts
```

---

## 16. Project Structure

```
lerm/
├── lerm/                          # Core Python package (21 modules)
│   ├── __init__.py
│   ├── stats.py                   # Statistical core (pass^k, CI, power, sequential testing)
│   ├── skeptic.py                 # Adversarial L0 skeptic (5-attack suite)
│   ├── firewall.py                # Fail-closed data firewall
│   ├── candidate_pool.py          # 9-gate candidate admission pipeline
│   ├── candidate_schema.py        # 20-field immutable task unit schema
│   ├── calibration.py             # Phase D two-stage calibration
│   ├── confounds.py               # 10-dimension confound checklist
│   ├── trace.py                   # Immutable JSONL trace store
│   ├── prereg.py                  # Cryptographic pre-registration
│   ├── kb.py                      # Knowledge Base & settlement
│   ├── controller.py              # Deterministic loop controller
│   ├── evaluator.py               # Container-isolated pytest evaluator
│   ├── resource.py                # Hardware RAM monitor & OOM eviction
│   ├── guardrails.py              # Spend ceilings & kill-switch
│   ├── digest.py                  # Daily/weekly digest generator
│   ├── ledger.py                  # Append-only experiment ledger
│   ├── regression.py              # Regression detection
│   ├── repairability.py           # Treatment-independent classifier
│   ├── trace_purity.py            # Calibration trace purity auditor
│   ├── checkpoint.py              # Crash recovery checkpoint manager
│   └── adapters/
│       ├── __init__.py
│       └── openhands.py           # OpenHands agent-server HTTP adapter
│
├── tests/                         # Test suite (88 tests)
│   ├── test_core.py               # 27 core tests
│   ├── test_firewall.py           # 13 firewall tests
│   ├── test_candidate_adversarial.py  # 20 adversarial attack tests
│   ├── test_repairability.py      # 7 repairability tests
│   ├── test_skeptic_planted.py    # 7 planted skeptic tests
│   └── test_calibration_stage2.py # 14 calibration tests
│
├── docs/
│   ├── ARCHITECTURE.md            # Full technical architecture specification
│   ├── DECISIONS.md               # 6 canonical design decisions
│   ├── DEVIATIONS.md              # 10 documented protocol deviations
│   ├── SPEC.md                    # High-level specification
│   ├── ADR-0001-execution-plane.md  # Architecture Decision Record
│   ├── protocol/                  # 16 frozen protocol specifications
│   │   ├── 01_candidate_schema.md
│   │   ├── 02_repository_sampling_policy.md
│   │   ├── ...
│   │   └── 16_calibration_operating_characteristics.md
│   └── diagrams/                  # 6 SVG architecture diagrams
│       ├── 01_system_architecture_3d.svg
│       ├── ...
│       └── 06_roadmap_vision_3d.svg
│
├── scripts/                       # 12 executable scripts
│   ├── preflight.py               # Environment health check
│   ├── demo_offline.py            # Full offline demo
│   ├── run_causal_experiment.py   # Primary causal experiment runner
│   ├── generate_phase_d_candidates.py
│   ├── generate_compound_candidates.py
│   ├── run_phase_d_calibration.py
│   ├── run_phase_d_calibration_openhands.py
│   └── ...
│
├── preregistrations/              # SHA-256 sealed experiment manifests
│   ├── LE-0001.yaml
│   ├── EXP-LOOP-001.yaml
│   └── EXP-LOOP-002.yaml
│
├── findings/                      # Settled research findings
│   └── LE-0001.yaml               # Offline pilot (UNCERTAIN)
│
├── negative_results/              # Mandatory negative result documentation
│   ├── FINDING-EXP-LOOP-001.yaml  # REFUTED (confounded)
│   ├── FINDING-EXP-LOOP-002.yaml  # REFUTED (ceiling effect)
│   └── NEG-LIVE-0001.yaml         # REFUTED (pipeline defects)
│
├── holdout/                       # Historical holdout tasks (quarantined)
│   └── tasks/
│       ├── HOLDOUT-001.yaml ... HOLDOUT-004.yaml
│       └── _schema.yaml
│
├── data/phase-d/                  # Phase D calibration data & manifests
├── reports/                       # Audit reports & verification evidence
│   ├── PHASE_C_AUDIT_REPORT.md    # 20-gate Phase C freeze (all PASS)
│   ├── P0_LIVE_VERIFICATION.md
│   ├── GITHUB_PUBLICATION_REPORT.md
│   └── phase-d/                   # Phase D reports
│
├── pyproject.toml                 # Package configuration (v1.0.0)
├── requirements.txt               # Minimum dependencies
├── Makefile                       # Build targets
├── .env.example                   # Environment template
├── .gitignore                     # Comprehensive ignore rules
└── LICENSE                        # MIT License
```

---

## 17. Research Roadmap

<p align="center">
  <img src="docs/diagrams/06_roadmap_vision_3d.svg" alt="Research Roadmap" width="100%" />
</p>

| Phase | Status | Description |
|---|---|---|
| **Phase 0/1** | `COMPLETED` | Control plane foundation: pre-registration, firewall, skeptic, confounds, pass^k, KB, guardrails |
| **Phase B** | `COMPLETED` | Pilot trials (EXP-LOOP-001, 002) — refuted, ceiling effect discovered |
| **Phase C** | `COMPLETED` | Protocol freeze, adversarial audit (20/20), reproducibility verification, 26 artifacts hashed |
| **Phase D** | `IN PROGRESS` | Candidate generation & sequential calibration on `mewwts__addict` |
| **Phase 2/3** | `PLANNED` | EXP-LOOP-003 primary causal trial (N≥20 tasks × k=5 reruns) |
| **Phase 4/5** | `VISION` | 24/7 autonomous AI scientist: multi-cloud Ray execution, auto-pre-registration, LaTeX manuscript synthesis |

---

## 18. License & Citation

Distributed under the [MIT License](LICENSE).

```bibtex
@software{lerm2026,
  author = {Nia00-glitch},
  title = {LERM: Loop Engineering Research Machine — Causal Inference and Adversarial Verification for Autonomous Agent Loops},
  year = {2026},
  url = {https://github.com/Nia00-glitch/lerm}
}
```
