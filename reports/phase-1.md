# Phase report — P0 gate + P1 trace/analysis core (control plane)

What works (measured, offline, no network/Docker):
- 22/22 tests pass: `python3 tests/test_core.py` (16) + `tests/test_skeptic_planted.py` (6).
- `scripts/demo_offline.py` runs the full chain: power analysis -> sealed prereg (sha256) ->
  1800 traced runs -> pass^k -> confound checklist -> skeptic -> KB -> digest.
- Measured on that run: infra failure 0.28%, median LERM overhead 5.5% (budget 10%),
  verifier FAR 0.051 / FRR 0.036, effect C-vs-B +0.175 [+0.067, +0.282] over 60 tasks.
- Spend cap fired correctly at $3.78/h against a $3.00 cap and hard-stopped.
- Skeptic killed 3/3 planted spurious findings (confound, shortcut, noise) and spared the
  honest one. Kill rate logged.

What is NOT done, and why:
- P0 unverified: no Docker daemon and no network egress in the environment this was built in.
  `make preflight` is the gate; it exits 1 rather than proceed. ADR-0001 chooses Option A (WSL2).
- P2 harness, P3 parallel plane, P7 direction finder: all require P0 green plus network.
- Verdict on the demo finding is UNCERTAIN, not SUPPORTED, because skeptic attacks 1 and 4
  need the execution plane. Pending attacks are never counted as passes.

Spec changes made, with reasons: see `docs/DEVIATIONS.md` (6 items; the load-bearing one is
n_reruns >= 2k, demonstrated by a failing-then-fixed test).

Reproduce:
    pip install -r requirements.txt && make selftest && make demo && make preflight
