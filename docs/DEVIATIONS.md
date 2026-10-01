# Deviations from the spec, with reasons

Per §13: disagreements stated with evidence, not silent changes.

1. **`n_reruns >= 2k`, not `n_reruns == k`.** The spec says k>=5 reruns. With n == k the
   unbiased pass^k estimator can only return 0 or 1 per task, so the task-level CI blows up
   and honest effects get killed as noise. Demonstrated: at n=k=5, 60 tasks, a true 0.40 ->
   0.70 lift produced a CI of [+0.000, +0.200] and the skeptic killed it. At n=10, k=5 the
   same design is cleanly separated. Cost is 2x runs; the alternative is an unusable metric.
   Encoded as a regression test in `tests/test_skeptic_planted.py`.

2. **Bootstrap resamples tasks, not runs.** Tasks are the unit of generalisation. Resampling
   runs produces CIs that are far too narrow and is a common source of false positives in
   agent evaluations.

3. **DuckDB is optional.** JSONL is the source of truth; the analytical store falls back to
   stdlib SQLite when DuckDB is absent, so the trace layer works on a bare Python before
   anything is installed. DuckDB remains the target at scale.

4. **Skeptic attacks 1 and 4 return NEEDS_EXECUTION, not FAIL or PASS.** Attacks that need the
   execution plane cannot be evaluated before P3. A finding with pending attacks is UNCERTAIN.
   Marking them passed would be exactly the self-deception L0 exists to prevent.

5. **Spend cap default is deliberately low** ($3/h, $40/day). The offline demo trips it at
   1800 simulated runs, which is the intended behaviour. Raise it consciously in `.env`, per
   §9, rather than discovering the right number from a bill.

6. **Skeptic model family check is a hard error at construction.** The spec says "a different
   model"; same-family review (e.g. two Claude versions) is not independent, so the constructor
   refuses it rather than warning.

7. **EXP-LOOP-003 PRNG_SEED_REPO reconciliation (`61022`, not `10001`).** Protocol 02 §4 originally
   specified `PRNG_SEED_REPO = 10001` as an ad-hoc placeholder during drafting. Protocol 05
   established the Master Seed Hierarchy deriving all subsystem seeds from `MASTER_SEED = 20260921`,
   yielding `(MASTER_SEED + 101) % 100000 = 61022`. Reconciled during Phase D preflight to
   eliminate contradiction and preserve hierarchical seed derivation. Zero EXP-LOOP-003 primary or
   calibration candidates had been generated prior to this reconciliation.

8. **EXP-LOOP-003 repository pool restricted to `mewwts__addict.75284f95` only (DECISION-0002).**
   Repositories `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6`
   trigger `BASELINE_FAIL` under Protocol 02 §2: clean checkout fails `pytest` offline due
   to unpinned floating dependencies with no lockfile (`simplejson` for marshmallow; `tblib`,
   `diff-cover` etc. for sqlfluff). Installing floating PyPI packages is forbidden under Rules
   G5/G6. Formally authorized as Phase D-partial under DECISION-0002 (see `docs/DECISIONS.md`),
   sizing the candidate pool to K_max_single_repo = 7 independent tasks (one task per function under
   Protocol 12 §1), while marshmallow/sqlfluff offline dependency isolation proceeds on a parallel
   non-blocking track. Evidence: reports/phase-d/BASELINE_DEPENDENCY_AUDIT.md §G8-G9; docs/DECISIONS.md (DECISION-0002).

9. **Golden-copy preservation wrapper for SWE-smith `shutil.rmtree` behavior.** SWE-smith
   commit `9b74ac08` unconditionally calls `shutil.rmtree(repo)` at `generate.py:L184` after
   candidate generation. LERM maintains an immutable `.golden` reference clone and copies it
   to the working path before each generation invocation, then restores it after SWE-smith
   deletes the working copy. SWE-smith source code is NOT modified. Evidence:
   reports/phase-d/PHASE_D_REMEDIATION_DESIGN.md Part B.

10. **Autonomous tool interaction & compound mutation calibration policy (DECISION-0006).**
   Under Protocol 06 §1, single-shot calibration previously assumed zero in-loop verifier diagnostics.
   When evaluated under OpenHands, the agent has native terminal access and autonomously executes
   pytest during Turn 1, diagnosing tracebacks and causing single-function mutations on compact
   repositories to collapse to a 100% ceiling (empirically confirmed on CAND-001 and CAND-008).
   Formally authorized under DECISION-0006 (see `docs/DECISIONS.md`): in-agent bash testing is
   recognized as valid Turn-1 agent capability, candidate difficulty is adapted via compound
   (higher-order) mutations across interacting functions, and calibration execution is throttled
   to <= 15 trials/day to preserve the ₹0 budget and 200 RPD OpenRouter free-tier quota.
