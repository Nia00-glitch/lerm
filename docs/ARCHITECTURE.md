# LERM Architecture & Technical Specification

**Version**: `1.0.0` (P0/P1 Verified, Phase C Protocol Frozen)  
**System**: Loop Engineering Research Machine (LERM)  
**Principle**: `TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT`

---

## 1. Executive System Overview

The **Loop Engineering Research Machine (LERM)** is an automated causal experimentation and verification control plane designed to measure, verify, and stress-test autonomous software engineering agent loops.

Most claims in autonomous agent literature conflate model capability, compute asymmetry, benchmark contamination, and ungrounded verifiers with true algorithmic loop superiority. LERM solves this by treating the agent loop as an experimental intervention within a strict causal inference framework:

![System Architecture](diagrams/01_system_architecture_3d.svg)

---

## 2. Core Architectural Components

### 2.1 Layer 4: Scientific Governance & Adversarial Skeptic (L0)
- **Adversarial Skeptic (`lerm.skeptic`)**: An automated scientific auditor that attempts to refute candidate findings before they enter the knowledge base. It executes five distinct attack vectors:
  1. `1_replication_new_seeds`: Re-executes the experiment under orthogonal PRNG seeds.
  2. `2_confound_search`: Scans trace telemetry for compute, token, or order imbalances.
  3. `3_shortcut_hunt`: Identifies whether the agent passed by gaming the evaluator, taking static shortcuts, or bypassing the core problem.
  4. `4_alternative_explanation`: Tests whether a simpler baseline (e.g. single-shot prompt tuning) accounts for the observed effect.
  5. `5_noise_check`: Verifies whether the 95% confidence interval lower bound clears the pre-registered threshold ($\Delta \ge +0.05$).
  - *Invariant*: The Skeptic model MUST belong to a different model family than the agent under test (enforced in `lerm/skeptic.py:L142`).
- **Knowledge Base & Settlement (`lerm.kb`)**: Immutable registry of experimental findings.
  - Verdicts are strictly three-valued: `SUPPORTED`, `REFUTED`, or `UNCERTAIN`.
  - Hedging prose (e.g. *"promising"*, *"suggests"*, *"trend"*) is rejected fail-closed at schema validation.
  - Every finding MUST contain an explicit `unexplained` field documenting phenomena not accounted for by the primary hypothesis.
- **Safety & Drift Guardrails (`lerm.guardrails`)**:
  - Enforces three-tier spend ceilings: Hourly ($25), Daily ($200), and Weekly ($800).
  - Listens for `state/KILL` trigger file to cleanly halt containers and commit state.
  - Monitors canary prompts to detect silent API-side model weight updates.

---

### 2.2 Layer 3: Causal Control Plane & Data Firewall
- **Cryptographic Pre-Registration (`lerm.prereg`)**:
  - Requires hypotheses, metric definitions, task manifests, sample sizes ($k \ge 5, n \ge 2k$), stopping boundaries, and compute matching to be serialized to YAML and SHA-256 sealed BEFORE trial execution.
  - At runtime, `prereg.verify()` asserts that the git-tracked pre-registration has not been modified post-hoc.
- **Fail-Closed Data Firewall (`lerm.firewall`)**:
  - Prevents historical contamination from EXP-LOOP-002 holdouts (`HOLDOUT-001` through `HOLDOUT-004`).
  - Maintains an immutable registry of historical task IDs and fixture content SHA-256 hashes.
  - Validates tasks during manifest admission and trace ingestion; blocks tampered flags, string booleans, and copied fixture artifacts.
- **Deterministic Loop Controller (`lerm.controller`)**:
  - Manages trial execution across comparison arms: `loop_retry` (Arm A: naive retry without verification feedback) vs `loop_verify` (Arm B: in-loop verification and targeted repair).
  - Enforces identical episode budgets: maximum 3 turns, 16,000 tokens, and 120.0 seconds wallclock timeout.

---

### 2.3 Layer 2: L1 Trace Layer & Confound Balancing
- **Immutable Trace Store (`lerm.trace`)**:
  - Records every LLM generation, tool call, action diff, and container event to append-only JSONL files.
  - Enforces the non-merged 3-field outcome taxonomy:
    - `verified_success: bool` (independent ground-truth test passed)
    - `infra_failure: bool` (OOM, timeout, Docker failure, network abort)
    - `model_failure: bool` (agent generated incorrect code or syntax error)
  - Tracks LERM framework overhead ratio, ensuring measurement infrastructure accounts for $\le 10\%$ of runtime.
- **Mechanical Confound Checklist (`lerm.confounds`)**:
  - Programmatically audits 10 confound dimensions before any finding can be declared `CAUSAL_ELIGIBLE`:
    1. `equal_compute_wallclock`
    2. `equal_tokens`
    3. `equal_attempts`
    4. `equal_cost`
    5. `same_model_version`
    6. `no_model_drift_within_experiment`
    7. `comparable_task_order`
    8. `same_seed_policy`
    9. `same_task_set`
    10. `no_human_intervention`
- **Statistical Inference Core (`lerm.stats`)**:
  - Computes $\text{pass}^k$ using an unbiased minimum-variance combinatorial estimator:
    $$\hat{p}^k = \frac{\binom{c}{k}}{\binom{n}{k}}$$
    where $c$ is the number of successes across $n$ runs.
  - Distinguishes lucky flukes ($\text{pass}@k$) from deterministic reliability ($\text{pass}^k$).
  - Calculates paired bootstrap confidence intervals, two-proportion hypothesis tests, and sequential O'Brien-Fleming stopping boundaries.

---

### 2.4 Layer 1: Execution Plane & Isolated Sandbox
- **Container Sandbox (`ADR-0001 Option A`)**:
  - Ephemeral Docker containers created per trial.
  - Read-only test suite mounts ensure the agent cannot alter or game test files.
  - Offline network isolation prevents external telemetry or web leakage.
- **Independent Evaluator (`lerm.evaluator`)**:
  - Executes unit tests in the clean sandbox after agent completion.
  - The agent's self-reported claim is NEVER ingested as ground truth.
- **Hardware-Aware Resource Manager (`lerm.resource`)**:
  - Coordinates local inference on memory-constrained systems (e.g. 16GB RAM).
  - Actively monitors physical RAM via OS APIs and invokes Ollama's `keep_alive=0` model eviction endpoint to avoid OOM thrashing.

---

## 3. Data & Control Flow

The following sequence illustrates the complete lifecycle of a causal experiment:

![Data and Control Flow](diagrams/02_data_control_flow_3d.svg)

1. **Pre-Registration**: Researcher declares hypothesis, model, tasks, and budgets in YAML. The file is hashed with SHA-256 and committed to git.
2. **Task Pool Generation & Screening**: Candidate tasks are generated via procedural AST mutations in SWE-smith. Candidates pass through the fail-closed firewall and calibration gate without exposure to treatment loops.
3. **Controlled Execution**: The controller executes matched trials for `loop_retry` and `loop_verify` under strict turn and token caps.
4. **Telemetry Logging**: Action traces, token counts, and execution durations are streamed to `traces/<exp_id>.jsonl`.
5. **Ground-Truth Evaluation**: The independent evaluator executes unit tests in an ephemeral container.
6. **Confound Balancing & Analysis**: `confounds.py` audits balance across arms. `stats.py` calculates the paired effect $\Delta \text{pass}^k$.
7. **Skeptic Auditing**: The adversarial skeptic attacks the result across 5 vectors.
8. **Knowledge Base Entry**: If all checks pass, the finding is settled into `findings/` with immutable YAML metadata.

---

## 4. Verification & Evaluator Architecture

To guarantee that candidate tasks are valid, repairable, and non-trivial, all tasks pass through an 8-stage verification chain before admission:

![Verification Architecture](diagrams/04_verification_eval_3d.svg)

- **Step A & B (Baseline)**: Verify clean repository passes all tests (`Exit 0`).
- **Step C & D (Mutation)**: Apply procedural AST mutation; verify tests fail (`Exit != 0`).
- **Step E & F (Repair)**: Apply inverse reference patch; verify tests pass (`Exit 0`).
- **Step G & H (Reset)**: Reset workspace to mutated fixture; assert `RESET_HASH == MUTATED_HASH`.

Any candidate that fails any step is immediately rejected and categorized under the deterministic rejection taxonomy:
- `baseline_failure`: Repository baseline broken.
- `mutation_no_effect`: Mutation does not cause semantic test failure.
- `infrastructure_failure`: OOM, timeout, or container fault.
- `evaluator_failure`: Syntax error in test harness.
- `reference_repair_failure`: Task cannot be repaired by reference fix.
- `historical_firewall_breach`: Matches quarantined historical holdout.

---

## 5. Failure Classification & Recovery Architecture

LERM strictly isolates infrastructure dropouts from agent capability measurements:

![Failure and Recovery Flow](diagrams/05_failure_recovery_flow_3d.svg)

1. **Hardware OOM / Memory Pressure**:
   - Monitored by `lerm.resource`.
   - When RAM drops below 2048 MB, Ollama models are proactively evicted to disk.
   - Container OOM kills (Exit 137) are tagged `infra_failure=True` and excluded from model success denominators.
2. **Agent Runaway / Infinite Loops**:
   - Monitored by `lerm.controller`.
   - Hard 120.0s wallclock timer triggers container termination.
   - Partial traces are captured; trial is marked `verified_success=False`.
3. **Emergency Kill-Switch**:
   - Touching `state/KILL` immediately halts the experiment loop, flushes in-flight telemetry, and prevents subsequent episode launches.

---

## 6. Implementation Status Matrix

| Component | Status | Code Location | Verification Evidence |
|---|---|---|---|
| Sealed Pre-Registration | **IMPLEMENTED & VERIFIED** | `lerm/prereg.py` | 27 core unit tests passing |
| Data Firewall (Historical Quarantine) | **IMPLEMENTED & VERIFIED** | `lerm/firewall.py` | 13 regression tests passing |
| Adversarial Skeptic (L0) | **IMPLEMENTED & VERIFIED** | `lerm/skeptic.py` | 7 planted attack tests passing |
| Confound Auditor | **IMPLEMENTED & VERIFIED** | `lerm/confounds.py` | 10-dimension balance verification |
| Unbiased Pass^k Estimator | **IMPLEMENTED & VERIFIED** | `lerm/stats.py` | Combinatorial unit tests passing |
| Candidate Schema & Pool Manager | **IMPLEMENTED & VERIFIED** | `lerm/candidate_pool.py` | 20 adversarial attack tests passing |
| SWE-smith Bit-Reproducibility | **IMPLEMENTED & VERIFIED** | `verify_3_configs_reproducibility.py` | 100% bit-for-bit across 3 configs |
| Hardware Resource Eviction | **IMPLEMENTED & VERIFIED** | `lerm/resource.py` | Memory status API & Ollama eviction |
| Phase D Primary Task Generation | **PLANNED** | `scripts/generate_primary_pool.py` | Ready for execution post Phase C freeze |
| EXP-LOOP-003 Primary Trial | **PLANNED** | `scripts/run_causal_experiment.py` | Pre-registered; awaiting Phase D pool |
| Autonomous 24/7 Research Loop | **VISION** | `docs/diagrams/06_roadmap_vision_3d.svg` | Multi-cloud SkyPilot cluster & auto-prereg |
