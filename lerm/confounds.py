"""Mechanical confound checklist (spec §5.6).

A causal claim is only allowed once every check below passes on the actual run
records. If any check fails the result is downgraded to CORRELATIONAL. This runs
on data, not on the experimenter's good intentions.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

import numpy as np

# Tolerated relative imbalance between conditions before a check fails.
DEFAULT_TOLERANCE = 0.05


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ConfoundReport:
    checks: list[Check]

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def verdict(self) -> str:
        return "CAUSAL_ELIGIBLE" if self.all_passed else "CORRELATIONAL"

    def failures(self) -> list[str]:
        return [c.name for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "checks": [c.to_dict() for c in self.checks]}


def _balance(a: Sequence[float], b: Sequence[float], tol: float) -> tuple[bool, str]:
    ma, mb = float(np.mean(a)), float(np.mean(b))
    base = max(abs(ma), abs(mb), 1e-9)
    rel = abs(ma - mb) / base
    return rel <= tol, f"mean {ma:.4g} vs {mb:.4g} (rel diff {rel:.2%}, tol {tol:.0%})"


def check_conditions(
    control_runs: Iterable[dict],
    treatment_runs: Iterable[dict],
    tolerance: float = DEFAULT_TOLERANCE,
) -> ConfoundReport:
    """Run records are dicts as emitted by lerm.trace.RunRecord.to_dict()."""
    c = list(control_runs)
    t = list(treatment_runs)
    checks: list[Check] = []

    if not c or not t:
        return ConfoundReport([Check("nonempty", False, "a condition has zero runs")])

    def field(runs, key, default=0.0):
        return [float(r.get(key, default) or 0.0) for r in runs]

    for name, key in (
        ("equal_compute_wallclock", "wallclock_s"),
        ("equal_tokens", "total_tokens"),
        ("equal_attempts", "attempts"),
        ("equal_cost", "cost_usd"),
    ):
        ok, detail = _balance(field(c, key), field(t, key), tolerance)
        checks.append(Check(name, ok, detail))

    # Same model version across both arms — silent provider drift invalidates everything.
    mc = {r.get("model_id") for r in c}
    mt = {r.get("model_id") for r in t}
    checks.append(Check(
        "same_model_version",
        mc == mt and len(mc) == 1 and None not in mc,
        f"control={sorted(map(str, mc))} treatment={sorted(map(str, mt))}",
    ))

    fc = {r.get("model_fingerprint") for r in c}
    ft = {r.get("model_fingerprint") for r in t}
    checks.append(Check(
        "no_model_drift_within_experiment",
        len(fc | ft) <= 1,
        f"fingerprints seen: {sorted(map(str, fc | ft))}",
    ))

    # Task ordering must not correlate with condition (learning/caching effects).
    oc, ot = field(c, "task_index"), field(t, "task_index")
    ok, detail = _balance(oc, ot, 0.20)
    checks.append(Check("comparable_task_order", ok, detail))

    # Seed policy: same seed multiset per arm, otherwise you compared seeds, not conditions.
    sc = sorted(str(r.get("seed")) for r in c)
    st = sorted(str(r.get("seed")) for r in t)
    checks.append(Check(
        "same_seed_policy",
        sc == st,
        f"{len(set(sc))} distinct seeds control / {len(set(st))} treatment; multisets "
        f"{'match' if sc == st else 'DIFFER'}",
    ))

    # Same task set, paired.
    tc = {r.get("task_id") for r in c}
    tt = {r.get("task_id") for r in t}
    checks.append(Check(
        "same_task_set",
        tc == tt,
        f"{len(tc & tt)} shared, {len(tc ^ tt)} unmatched",
    ))

    # Any human touched the trace -> not an autonomous result.
    touched = [r.get("run_id") for r in c + t if r.get("human_intervention")]
    checks.append(Check(
        "no_human_intervention",
        not touched,
        f"{len(touched)} run(s) flagged" + (f": {touched[:3]}" if touched else ""),
    ))

    return ConfoundReport(checks)
