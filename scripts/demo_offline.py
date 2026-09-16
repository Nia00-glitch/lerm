#!/usr/bin/env python3
"""End-to-end dry run of everything that does NOT need Docker, GPUs or network.

Exercises the real code path: power analysis -> sealed preregistration ->
traced runs -> pass^k -> confound checklist -> adversarial skeptic ->
knowledge base -> daily digest. The agent executions are simulated (clearly
labelled `SIMULATED` in every artifact) because the execution plane lives on
your machine, not here.

    python3 scripts/demo_offline.py

Real artifacts land in preregistrations/, traces/, findings/, negative_results/,
reports/daily/ and store/ so you can see exactly what the machine emits.
"""
from __future__ import annotations

import os
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm import confounds as cf, digest, kb, stats as st, trace
from lerm.guardrails import BudgetExceeded, Caps, SpendLedger, check_drift
from lerm.prereg import Preregistration
from lerm.skeptic import Skeptic, kill_rate

MODEL_UT = "qwen/qwen3-coder-480b"       # placeholder: pin a real OmniRoute ID
MODEL_SKEPTIC = "deepseek/deepseek-v3"   # different family, enforced by Skeptic
EXP = "LE-0001"


def simulate(condition: str, n_tasks: int, n_reruns: int, p_base: float, lift: float,
             seed: int, writer: trace.TraceWriter, ledger: SpendLedger) -> list[dict]:
    """Compute-matched simulated runs. Only the success rate differs by condition."""
    rng = random.Random(seed)
    out = []
    for ti in range(n_tasks):
        task_skill = rng.betavariate(2, 2)            # task difficulty, shared across arms
        for ri in range(n_reruns):
            rec = trace.RunRecord(
                experiment_id=EXP, prereg_id=EXP, task_id=f"HOLDOUT-{ti:03d}",
                condition=condition, seed=1000 + ri, model_id=MODEL_UT,
                model_fingerprint="fp_2026_09", task_index=ti, rerun_index=ri,
            )
            rec.record_llm(model_id=MODEL_UT, model_fingerprint="fp_2026_09",
                           prompt_tokens=1800, completion_tokens=700, cached_tokens=1200,
                           latency_s=2.4, cost_usd=0.0021)
            rec.record_tool("bash", 0.8, True)
            rec.attempts = 3
            rec.wallclock_s = 58.0 + rng.random() * 4
            rec.overhead_s = 3.1 + rng.random() * 0.4      # <10% budget
            gt = rng.random() < min(0.97, p_base * (0.5 + task_skill) + lift)
            rec.ground_truth = gt
            # The verifier is imperfect on purpose — we measure it, we don't trust it.
            rec.verifier_said = gt if rng.random() > 0.06 else (not gt)
            rec.agent_claimed = True if gt or rng.random() < 0.35 else False
            rec.infra_failure = rng.random() < 0.004
            rec.finish()
            writer.write(rec)
            ledger.record(rec.cost_usd, EXP)
            out.append(rec.to_dict())
    return out


def main() -> int:
    for d in ("preregistrations", "traces", "findings", "negative_results", "state",
              "reports/daily", "store"):
        shutil.rmtree(d, ignore_errors=True)

    # ---- L4: power analysis decides N and k, not vibes ---------------------
    plan = st.plan_experiment(baseline_rate=0.62, mde=0.08, k=5, power=0.80)
    print(f"[L4] power analysis -> n_tasks={plan.n_tasks}, k={plan.k_reruns}, "
          f"runs/condition={plan.runs_per_condition}")
    n_tasks, k, n_reruns = min(plan.n_tasks, 60), plan.k_reruns, 10

    # ---- L5: pre-register BEFORE running, sealed by hash ------------------
    hypothesis = ("Independent verification in the loop improves pass^5 verified success "
                  "more than an equal-compute increase in retries, on the private held-out set.")
    if prior := kb.already_settled(hypothesis):
        print(f"[L5] refusing to re-run: already settled as {prior['status']} in {prior['id']}")
        return 0
    prereg = Preregistration(
        id=EXP, hypothesis=hypothesis,
        conditions=["A_baseline", "B_extra_retries", "C_independent_verifier"],
        primary_metric="verified_success_pass_k",
        secondary_metrics=["reliability_gap", "verifier_false_accept_rate"],
        n_tasks=n_tasks, k_reruns=k, private_holdout_n=n_tasks,
        models=[MODEL_UT], decision_threshold=0.05, alpha=0.05, power=0.80,
        compute_matching="C is token- and wallclock-matched to B; both matched to A + delta",
        predicted_failure_mode="C wins on agent_claimed but not on ground_truth",
    )
    print(f"[L5] sealed {prereg.seal()} (hash {prereg.content_hash()[:12]})")

    # ---- L1/L2: traced (simulated) execution ------------------------------
    writer = trace.TraceWriter(EXP)
    ledger = SpendLedger(Caps(usd_per_hour=3, usd_per_day=40, usd_per_week=200))
    a = simulate("A_baseline", n_tasks, n_reruns, 0.62, 0.00, 11, writer, ledger)
    b = simulate("B_extra_retries", n_tasks, n_reruns, 0.62, 0.04, 12, writer, ledger)
    c = simulate("C_independent_verifier", n_tasks, n_reruns, 0.62, 0.14, 13, writer, ledger)
    runs = a + b + c
    try:
        ledger.assert_within_caps()
    except BudgetExceeded as e:
        # This firing is the feature working, not a bug: 1800 runs blew the default
        # hourly cap. Raise it deliberately for the dry run and move on.
        print(f"[G9] spend cap fired as designed -> {e}")
        ledger.caps = Caps(usd_per_hour=25, usd_per_day=200, usd_per_week=800)
        ledger.assert_within_caps()
    print(f"[L1] {len(runs)} runs traced -> traces/{EXP}.jsonl | "
          f"infra failures {trace.infra_failure_rate(runs):.2%} | "
          f"median overhead {trace.median_overhead_ratio(runs):.1%}")
    print(f"[L1] {trace.build_store([EXP])}")

    # ---- analysis, gated by the sealed preregistration ---------------------
    from lerm.prereg import assert_declared
    assert_declared(EXP, "verified_success_pass_k")

    by = {cond: trace.group_by_task(runs, cond)
          for cond in ("A_baseline", "B_extra_retries", "C_independent_verifier")}
    for cond, d in by.items():
        print(f"[L1] {cond:<24} pass^{k}={st.task_level_pass_hat_k(d, k):.3f}  "
              f"pass@{k}={st.pass_at_k(sum(d.values(), []), k):.3f}")

    effect = st.paired_effect_pass_hat_k(by["B_extra_retries"], by["C_independent_verifier"], k=k)
    print(f"[L4] effect C-vs-B on pass^{k}: {effect.value:+.3f} "
          f"[{effect.ci_low:+.3f}, {effect.ci_high:+.3f}] over {effect.n_tasks} tasks")

    ver = st.verifier_quality([r["verifier_said"] for r in c], [r["ground_truth"] for r in c])
    print(f"[L1] verifier FAR={ver.false_accept_rate:.3f} FRR={ver.false_reject_rate:.3f}")

    report = cf.check_conditions(b, c)
    print(f"[L0] confound checklist: {report.verdict} "
          f"({len(report.checks) - len(report.failures())}/{len(report.checks)} passed)")

    # ---- L0: the skeptic tries to kill it ---------------------------------
    sk = Skeptic(MODEL_SKEPTIC, MODEL_UT)
    verdict = sk.interrogate(EXP, b, c, effect, threshold=prereg.decision_threshold)
    for att in verdict.attacks:
        print(f"[L0]   {att.attack:<28} {att.status:<15} {att.detail[:80]}")
    print(f"[L0] verdict: {verdict.status}")

    # ---- knowledge base ---------------------------------------------------
    finding = kb.from_skeptic(
        finding_id=EXP, hypothesis=hypothesis, prereg_id=EXP, verdict=verdict, effect=effect,
        confound_report=report, verifier=ver, runs=b + c, models=[MODEL_UT],
        scope_limits=(f"holds only for the {n_tasks}-task private holdout under the "
                      "compute budget in the prereg; untested beyond one model family"),
        unexplained=("why the reliability gap between pass@k and pass^k is larger for C than "
                     "for B is not explained by the verifier FAR alone"),
        next_questions=["does the effect survive on a second model family?",
                        "does verifier FAR grow with task horizon?"],
    )
    path = finding.save()
    ok, why = finding.is_principle_eligible()
    print(f"[KB] wrote {path} status={finding.status} causal={finding.causal_verdict}")
    print(f"[KB] principle eligible: {ok} ({why})")

    # ---- guardrails + digest ---------------------------------------------
    drift = check_drift(MODEL_UT, ["canary-1-output", "canary-2-output"], "fp_2026_09")
    print(f"[G9] drift canary: {drift.detail}")
    d = digest.build(
        ledger=ledger, queue=["LE-0002 scaffold shape as independent variable"],
        skeptic_kill_rate=kill_rate([verdict]),
        infra_failure_rate=trace.infra_failure_rate(runs),
        overhead_ratio=trace.median_overhead_ratio(runs),
    )
    print(f"[G9] digest -> {d}")
    print("\nNOTE: agent executions above were SIMULATED. Real numbers require the "
          "execution plane (P0/P2/P3) on your machine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
