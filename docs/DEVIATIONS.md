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
