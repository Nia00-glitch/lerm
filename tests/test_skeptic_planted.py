"""P5 acceptance test — runs offline, no network, no Docker.

Three planted findings:
  1. spurious-by-confound   : treatment silently gets 2x the token budget
  2. spurious-by-shortcut   : the wins come from editing the test files
  3. spurious-by-noise      : a real-looking lift that is inside the CI at this N
and one honest finding that must SURVIVE.

If the skeptic kills the honest one, it is too aggressive and useless.
If it fails to kill any planted one, the whole L0 layer is theatre.
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm import confounds as cf
from lerm import stats as st
from lerm.skeptic import Skeptic


def make_runs(condition, n_tasks, n_reruns, p, seed, tokens=1000, model="qwen/qwen3-coder",
              fingerprint="fp_a", shortcut=False, seeds_shared=True):
    rng = random.Random(seed)
    runs = []
    for ti in range(n_tasks):
        for ri in range(n_reruns):
            ok = rng.random() < p
            tool_calls = []
            if ok and shortcut:
                tool_calls.append({"name": "str_replace tests/test_solution.py", "error": None})
            runs.append({
                "run_id": f"{condition}-{ti}-{ri}",
                "task_id": f"T{ti:03d}",
                "condition": condition,
                "seed": (1000 + ri) if seeds_shared else (9000 + ri + ti),
                "task_index": ti,
                "model_id": model,
                "model_fingerprint": fingerprint,
                "attempts": 3,
                "total_tokens": tokens,
                "cost_usd": tokens * 3e-6,
                "wallclock_s": 60.0,
                "overhead_s": 3.0,
                "human_intervention": False,
                "infra_failure": False,
                "verified_success": ok,
                "tool_calls": tool_calls,
                "shortcut_flags": [],
            })
    return runs


def by_task(runs):
    out = {}
    for r in runs:
        out.setdefault(r["task_id"], []).append(bool(r["verified_success"]))
    return out


def evaluate(name, control, treatment, threshold=0.02, k=5):
    sk = Skeptic(skeptic_model="deepseek/deepseek-v3", model_under_test="qwen/qwen3-coder")
    effect = st.paired_effect_pass_hat_k(by_task(control), by_task(treatment), k=k)
    verdict = sk.interrogate(name, control, treatment, effect, threshold)
    return verdict, effect


def test_confounded_finding_is_killed():
    control = make_runs("baseline", 40, 5, 0.55, seed=1, tokens=1000)
    treatment = make_runs("verifier", 40, 5, 0.75, seed=2, tokens=2000)  # 2x compute
    verdict, _ = evaluate("PLANT-1", control, treatment)
    assert verdict.killed, "skeptic missed a compute confound"
    assert any("confound" in r for r in verdict.kill_reasons())


def test_shortcut_finding_is_killed():
    control = make_runs("baseline", 40, 5, 0.55, seed=3)
    treatment = make_runs("verifier", 40, 5, 0.75, seed=4, shortcut=True)
    verdict, _ = evaluate("PLANT-2", control, treatment)
    assert verdict.killed, "skeptic missed reward hacking in the winning traces"
    assert any("shortcut" in r for r in verdict.kill_reasons())


def test_noise_finding_is_killed():
    control = make_runs("baseline", 12, 5, 0.50, seed=5)
    treatment = make_runs("verifier", 12, 5, 0.52, seed=6)  # tiny lift, small N
    verdict, effect = evaluate("PLANT-3", control, treatment, threshold=0.05)
    assert verdict.killed, f"skeptic accepted noise: {effect}"
    assert any("noise" in r for r in verdict.kill_reasons())


def test_honest_finding_survives_offline_attacks():
    # n_reruns > k on purpose: with n == k the pass^k estimator collapses to a
    # binary per-task 0/1 and the CI blows up. Budget n >= 2k for graded estimates.
    control = make_runs("baseline", 60, 10, 0.55, seed=7)
    treatment = make_runs("verifier", 60, 10, 0.85, seed=8)
    verdict, effect = evaluate("HONEST-1", control, treatment, threshold=0.02)
    assert not verdict.killed, f"skeptic killed an honest finding: {verdict.kill_reasons()}"
    # Attacks 1 and 4 need the execution plane, so an honest finding is UNCERTAIN
    # until L3 exists. It is never silently promoted to SUPPORTED.
    assert verdict.status == "UNCERTAIN"
    assert effect.ci_low > 0.02


def test_skeptic_refuses_same_model_family():
    try:
        Skeptic(skeptic_model="anthropic/claude-x", model_under_test="claude-y")
    except ValueError:
        return
    raise AssertionError("skeptic allowed same-family self-review")


def test_confound_checklist_flags_seed_policy():
    control = make_runs("baseline", 20, 5, 0.5, seed=9, seeds_shared=True)
    treatment = make_runs("verifier", 20, 5, 0.5, seed=10, seeds_shared=False)
    report = cf.check_conditions(control, treatment)
    assert "same_seed_policy" in report.failures()
    assert report.verdict == "CORRELATIONAL"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    raise SystemExit(1 if failed else 0)
