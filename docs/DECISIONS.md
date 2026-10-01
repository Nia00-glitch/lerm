# LERM Canonical Decision Ledger
**Authority:** Governed by LERM Operating Protocol v2 (§29).  
**Purpose:** Single authoritative source of truth for contested, amended, or resolved protocol decisions.

No document in this repository may assert a resolved state for a question unless a corresponding entry exists in this ledger.

---

## Decision Entries

### DECISION-0001
- **DECISION_ID:** DECISION-0001
- **QUESTION:** What is the governing operating protocol for engineering execution, verification, and research validity in LERM?
- **OPTIONS CONSIDERED:**
  1. Continue with legacy LERM Protocol v1 (undated, lacked 6th pass, cross-document scan, independent recomputation, placeholder quarantine, completion ledgers, and formal self-integrity hashing).
  2. Adopt LERM — STRICT LOOP ENGINEERING OPERATING PROTOCOL (v2) (PROTOCOL_VERSION: 2.0).
- **RESOLUTION:** Adopt LERM — STRICT LOOP ENGINEERING OPERATING PROTOCOL (v2) as the mandatory, persistent operating discipline across all tasks in this repository. Formalize self-integrity under §25 by recording the exact cryptographic SHA-256 hash of `PROTOCOL.md`.
- **CONTENT_SHA256 (PROTOCOL.md):** `D753F115EAE1C7877DE80BA5C2187688716CF624ED29CF2794EC4BCB749A0F45`
- **RESOLVED BY:** user (explicit directive to apply strictly across all tasks)
- **DATE:** 2026-09-23
- **SUPERSEDES:** v1 (undated)
- **DOWNSTREAM DOCS TO UPDATE:**
  - `PROTOCOL.md` (authoritative protocol specification)
  - `AGENTS.md` (workspace project rule for Antigravity engine)
  - `GEMINI.md` (workspace rule for Gemini/Antigravity IDE)
  - `.agents/rules/lerm_protocol_v2.md` (workspace customization rule)

### DECISION-0002
- **DECISION_ID:** DECISION-0002
- **QUESTION:** How shall EXP-LOOP-003 candidate generation and candidate pool architecture proceed given baseline dependency failures in `marshmallow` and `sqlfluff` and the structural function ceiling in `mewwts__addict.75284f95`?
- **OPTIONS CONSIDERED:**
  1. Halt entire project until offline dependencies for `marshmallow` and `sqlfluff` are completely isolated and pinned in offline containers (Path A).
  2. Forcibly generate $K=30$ tasks from `addict` alone by violating Protocol 12 §1 (clustering multiple mutations in `__init__`, `__setitem__`, etc.).
  3. Proceed immediately with Phase D-partial using a single-repo (`addict`-only) candidate pool honestly sized to `K_max_single_repo = 7` recomputed under strict one-task-per-function independence, while `marshmallow` and `sqlfluff` dependency resolution (Path A) continues in parallel as a non-blocking track for a future expanded pool.
- **RESOLUTION:** Proceed with Phase D-partial on `mewwts__addict.75284f95`. Recomputed AST structural analysis reveals 22 total FunctionDef nodes, of which exactly 14 qualify under the 5 allowed mutation rules. The initial execution cohort evaluated $K = 7$ tasks because the first SWE-smith batch only generated mutations covering 7 distinct functions (`setdefault`, `__init__`, `_hook`, `freeze`, `to_dict`, `__setitem__`, `update`). The remaining 7 qualifying functions (`__setattr__`, `__add__`, `__missing__`, `__deepcopy__`, `__or__`, `__ror__`, `__ior__`) constitute the second cohort to reach full structural ceiling $K_{\max} = 14$. Dependency resolution for `marshmallow` and `sqlfluff` (Path A) continues in parallel as a non-blocking track for future candidate pool expansion.
- **STATISTICAL POWER AUDIT (lerm.stats.plan_experiment):**
  At $N = 7$ tasks ($k = 5$ reruns, baseline pass rate $p_0 = 0.50^5 = 0.03125$, $\alpha = 0.05$), statistical power to detect MDE = 0.20 is 18.62% (standard 80% power requires $N \ge 44$ tasks; for $N = 7$, 80% power requires MDE $\approx 0.66$). For full single-repo ceiling $N = 14$, power to detect MDE = 0.20 is 35.8%. Statistical power is acknowledged as restricted for single-repo cohorts.
- **RESOLVED BY:** User Directive and LERM Lead Execution Agent under Protocol v2 (§7, §27, §29)
- **DATE:** 2026-09-23 (Amended 2026-09-27 with K_max=14 AST reconciliation)
- **SUPERSEDES:** Prior informal "K<=7" estimate in `FINAL_PRE_D1_APPROVAL_AUDIT.md` and un-gated execution attempts.
- **DOWNSTREAM DOCS TO UPDATE:**
  - `docs/DEVIATIONS.md` (Item 8: reference DECISION-0002 by ID)
  - `data/phase-d/candidates_manifest.yaml` (track cohort 1 vs cohort 2)
  - `scripts/generate_phase_d_candidates.py` (mechanical gate verification)

### DECISION-0003
- **DECISION_ID:** DECISION-0003
- **QUESTION:** How is execution mechanism parity established between Phase D single-shot difficulty calibration and EXP-LOOP-003 multi-turn agent experiment execution?
- **OPTIONS CONSIDERED:**
  1. Mandate that calibration must run through the OpenHands agent-server container (`ghcr.io/openhands/agent-server:1.26.0-python`) with single-turn limits.
  2. Maintain calibration via raw Ollama completions (`/api/generate`) and align EXP-LOOP-003 primary loop execution to the same native completion loop (`lerm/controller.py` with AST/pytest verifier feedback).
  3. Formally document the operational justification for raw completion calibration predicting agent-server loop difficulty while maintaining ₹0 local execution constraints.
- **RESOLUTION:** Option 2 / 3: Calibration difficulty under raw zero-feedback completion sets a strict upper bound on task intrinsic difficulty. EXP-LOOP-003 execution mechanism must maintain parity by using identical model inference pathways or explicitly accounting for agent-server scaffolding effects. If EXP-LOOP-003 runs through `lerm.controller` (native loop execution with verifier feedback), parity is directly preserved. If EXP-LOOP-003 runs through OpenHands, single-shot control arm must run through OpenHands to prevent cross-harness confounding.
- **RESOLVED BY:** LERM Execution Agent per Protocol v2 (§5, §14, §29)
- **DATE:** 2026-09-27

### DECISION-0004
- **DECISION_ID:** DECISION-0004
- **QUESTION:** Does single-shot calibration under the OpenHands agent-server diverge from raw completion calibration for `qwen2.5-coder:1.5b` on `mewwts__addict.75284f95`, and what mechanism shall be used to screen Cohort 2?
- **OPTIONS CONSIDERED:**
  1. Halt raw completion screening entirely; recalibrate all of Cohort 1 and future cohorts exclusively through OpenHands single-shot.
  2. Proceed with raw completion screening for Cohort 2 (the remaining 7 qualifying functions in `addict`) as a fast intrinsic capability screen, while establishing a mandatory OpenHands confirmation gate for any candidate admitted to the primary pool prior to EXP-LOOP-003 launch.
- **EMPIRICAL PROBE EVIDENCE (J2, n=20 trials + K1 neutral smoke):**
  - **CAND-001 (Floor Candidate):**
    - Raw completion: $\hat{p} = 0/10 = 0.0000$ [95% Wilson CI: $0.0000, 0.2775$]
    - OpenHands single-shot: $\hat{p} = 0/10 = 0.0000$ [95% Wilson CI: $0.0000, 0.2775$]
    - Parity Delta: $+0.0000$
    - Actions taken: 0/10 (model emitted JSON summaries/draft PR schemas, never invoked bash/editor tools)
  - **CAND-008 (Near-Band Candidate):**
    - Raw completion: $\hat{p} = 3/20 = 0.1500$ [95% Wilson CI: $0.0524, 0.3604$]
    - OpenHands single-shot: $\hat{p} = 0/10 = 0.0000$ [95% Wilson CI: $0.0000, 0.2775$]
    - Parity Delta: $-0.1500$
    - Actions taken: 0/10 (model emitted JSON summaries/draft PR schemas, never invoked bash/editor tools)
  - **K1 Neutral Smoke Test Reconfirmation:** A neutral trivial task ("list files in /workspace/project using bash") dispatched to `qwen2.5-coder:1.5b` under the identical OpenHands harness yielded 0 ActionEvents and emitted chat text (`{"type": "message", "message": "Listing files..."}`).
  - **Scope Limitation & Model Limitation Correction:** The 0/20 failure under OpenHands is a reconfirmation of an already-known model limitation (`qwen2.5-coder:1.5b` failing OpenHands tool schema invocation), NOT a task-difficulty finding. Furthermore, this directional finding was observed strictly on 2 candidates already at or near the floor under raw completion (CAND-001 at 0/10, CAND-008 at 3/20), was not validated on any candidate inside the target admission band ($0.35 \le p \le 0.65$), and is NOT a general claim about the relationship between the two mechanisms.
- **RESOLUTION:** Adopt Option 2 with explicit scope bounds: Raw completion serves only as a computationally cheap ($5\times$ faster) coarse preliminary screen for gross invalidity (e.g. unparseable syntax, catastrophic regressions). Because `qwen2.5-coder:1.5b` cannot execute tool actions in OpenHands, its calibration numbers do not govern admission to EXP-LOOP-003. Final admission to the primary experimental pool requires evaluation under the confirmed EXP-LOOP-003 agent-under-test model.
- **RESOLVED BY:** Lead LERM Execution Agent per Protocol v2 (§3, §26, §29) and User Directives J3/K4
- **DATE:** 2026-09-27 (Amended 2026-09-27 per K1/K4)
- **ARTIFACTS:** `scratch/openhands_probe_traces.jsonl`, `scratch/openhands_probe_summary.json`, `scratch/k1_smoke_events.json`

### DECISION-0005
- **DECISION_ID:** DECISION-0005
- **QUESTION:** Which model is the confirmed, authoritative agent-under-test for EXP-LOOP-003 execution and difficulty calibration?
- **OPTIONS CONSIDERED:**
  1. Continue using local `qwen2.5-coder:1.5b` (or `:3b`) as agent-under-test in OpenHands.
  2. Formally designate and pin `openrouter/thinkingmachines/inkling-small:free` as the official EXP-LOOP-003 agent-under-test.
- **EMPIRICAL & CONFIGURATION EVIDENCE:**
  - Runtime config `.env` explicitly declares: `LLM_MODEL=openrouter/thinkingmachines/inkling-small:free`.
  - Driver script `scripts/run_causal_experiment.py:L49` reads: `DEFAULT_MODEL = os.environ.get("LLM_MODEL", "openrouter/thinkingmachines/inkling-small:free")`.
  - Smoke tests in `smoke_events_inkling.json` confirm `openrouter/thinkingmachines/inkling-small:free` successfully executes real OpenHands `TerminalAction` events (`ls -la /workspace/project`), whereas `qwen2.5-coder:1.5b` takes 0 tool actions across 100% of tested trials (K1 and J2).
  - Protocol §14 ("MODEL / TOOL VERIFICATION") requires models to be verified before use; `qwen2.5-coder:1.5b` is disqualified as an autonomous OpenHands agent.
- **RESOLUTION:** Disqualify `qwen2.5-coder:1.5b` (and `:3b`) from serving as the agent-under-test. Formally confirm and pin `openrouter/thinkingmachines/inkling-small:free` as the authoritative agent-under-test for EXP-LOOP-003. Consequently, Cohort 1 calibration results collected under `qwen2.5-coder:1.5b` do not transfer to EXP-LOOP-003 task gating and must be recalibrated under the real agent-under-test model.
- **RESOLVED BY:** Lead LERM Execution Agent per Protocol v2 (§7, §14, §29) and User Directive K2
- **DATE:** 2026-09-27
- **ARTIFACTS:** `.env`, `scripts/run_causal_experiment.py`, `smoke_events_inkling.json`

### DECISION-0006
- **DECISION_ID:** DECISION-0006
- **QUESTION:** How should LERM resolve the tool-assisted verifier leakage (ceiling effect where single-function mutations pass Turn 1 at 100%) and the OpenRouter free-tier 200 RPD API quota barrier during Phase D difficulty calibration?
- **OPTIONS CONSIDERED:**
  1. Sandbox test isolation (`chmod 000 test_addict.py` during calibration so the agent cannot run pytest via bash, enforcing Protocol 06 §1 zero-verifier-diagnostics purity).
  2. Raw completion screening as standard difficulty benchmark (isolates intrinsic repair capability without tool-loop leakage, eliminating OpenRouter API quota limits).
  3. Paced multi-day OpenHands calibration with harder candidates (treats in-agent bash testing as a valid capability, requiring harder/multi-file mutations and multi-day execution).
- **RESOLUTION:** Adopt Option 3:
  1. **Autonomous Tool Interaction Policy**: Treat in-agent bash interaction (including running tests, viewing tracebacks, and using unix tools) as a valid native capability of the autonomous agent during its turn in OpenHands.
  2. **Difficulty Adaptation (Harder Candidates Required)**: Single-function, single-rule AST mutations on `addict` (Cohort 1) are too easy for `inkling-small:free` when equipped with bash/editor tools, causing an immediate ceiling collapse. Candidates must feature compound/multi-mutation, multi-function, or multi-file dependencies to land inside the $0.35 \le \hat{p} \le 0.65$ target admission band.
  3. **Execution Pacing & Daily Quota Discipline**: Because each OpenHands trial consumes ~8–12 LLM completions, execution must be batched across daily quotas (max 15 trials per day $\approx 150$ calls) with $\ge 4$s inter-call sleep to strictly preserve the ₹0 budget and avoid HTTP 429 rate limits.
- **RESOLVED BY:** User Directive (Option 3 selection) and LERM Execution Agent per Protocol v2 (§7, §13, §18, §29)
- **DATE:** 2026-09-28
- **DOWNSTREAM DOCS TO UPDATE:**
  - `docs/DECISIONS.md`
  - `docs/protocol/06_calibration_protocol.md` (documenting in-agent tool capability and multi-day pacing)
  - `docs/protocol/03_mutation_policy.md` (defining compound / harder mutation specification)
