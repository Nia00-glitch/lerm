"""Regression suite for the layers that decide what the machine is allowed to claim."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm import kb, stats as st, trace
from lerm.prereg import Preregistration, PreregViolation, assert_declared, verify
from lerm.regression import check_regression


# ------------------------------------------------------------------ stats

def test_pass_hat_k_is_unbiased_not_naive():
    s = [True] * 7 + [False] * 3            # n=10, c=7
    naive = (0.7) ** 5
    assert abs(st.pass_hat_k(s, 5) - 21 / 252) < 1e-12
    assert st.pass_hat_k(s, 5) < naive, "naive (c/n)**k must be the more optimistic one"


def test_pass_hat_k_zero_when_fewer_successes_than_k():
    assert st.pass_hat_k([True] * 3 + [False] * 7, 5) == 0.0


def test_reliability_gap_is_the_interesting_number():
    s = [True] * 8 + [False] * 2
    assert st.pass_at_k(s, 5) > st.pass_hat_k(s, 5)
    assert st.reliability_gap(s, 5) > 0.5


def test_effect_ci_contains_zero_for_identical_arms():
    d = {f"T{i}": [True] * 6 + [False] * 4 for i in range(30)}
    e = st.paired_effect_pass_hat_k(d, dict(d), k=5)
    assert e.value == 0.0 and e.crosses_zero()


def test_power_plan_demands_more_tasks_for_smaller_effects():
    big = st.plan_experiment(0.6, 0.15, k=5)
    small = st.plan_experiment(0.6, 0.03, k=5)
    assert small.n_tasks > big.n_tasks
    assert small.runs_per_condition == small.n_tasks * small.k_reruns


def test_sequential_boundary_is_strict_early():
    assert st.obrien_fleming_boundary(0.3) > st.obrien_fleming_boundary(1.0)
    assert not st.may_stop_early(2.1, 0.3)     # would be "significant" at a naive look
    assert st.may_stop_early(2.1, 1.0)


def test_verifier_quality_far_frr():
    v = [True, True, False, False, True]
    g = [True, False, False, True, True]
    q = st.verifier_quality(v, g)
    assert abs(q.false_accept_rate - 0.5) < 1e-9   # 1 of 2 true negatives accepted
    assert abs(q.false_reject_rate - (1 / 3)) < 1e-9


# ----------------------------------------------------------------- prereg

def _prereg(pid="LE-TEST"):
    return Preregistration(
        id=pid, hypothesis="X improves pass^5 over Y at equal compute",
        conditions=["A", "B"], primary_metric="verified_success_pass_k",
        secondary_metrics=["reliability_gap"], n_tasks=40, k_reruns=5,
    )


def test_prereg_is_immutable_and_hash_verified():
    tmp = tempfile.mkdtemp()
    try:
        p = _prereg()
        p.seal(tmp)
        verify("LE-TEST", tmp)
        try:
            p.seal(tmp)
        except PreregViolation:
            pass
        else:
            raise AssertionError("overwriting a sealed preregistration was allowed")
        path = os.path.join(tmp, "LE-TEST.yaml")
        open(path, "a").write("\nn_tasks: 999\n")
        try:
            verify("LE-TEST", tmp)
        except PreregViolation:
            return
        raise AssertionError("post-hoc edit of a sealed prereg went undetected")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_undeclared_metric_is_blocked():
    tmp = tempfile.mkdtemp()
    try:
        _prereg("LE-T2").seal(tmp)
        assert_declared("LE-T2", "verified_success_pass_k", tmp)
        try:
            assert_declared("LE-T2", "agent_claimed_success", tmp)
        except PreregViolation:
            return
        raise AssertionError("undeclared metric was allowed to support a finding")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_prereg_rejects_k_below_five():
    try:
        Preregistration(id="X", hypothesis="h", conditions=["A", "B"],
                        primary_metric="m", k_reruns=1)
    except ValueError:
        pass
    else:
        raise AssertionError("k_reruns < 5 was accepted")


def test_prereg_rejects_n_reruns_below_two_k():
    try:
        Preregistration(id="X", hypothesis="h", conditions=["A", "B"],
                        primary_metric="m", k_reruns=5, n_reruns=5)
    except ValueError as e:
        assert "n_reruns" in str(e)
        return
    raise AssertionError("n_reruns < 2*k_reruns was accepted")


# ------------------------------------------------------------------- trace

def test_verified_success_never_uses_agent_claim():
    r = trace.RunRecord(experiment_id="E", prereg_id="E", task_id="T", condition="A",
                        seed=1, model_id="m")
    r.agent_claimed = True
    try:
        r.verified_success()
    except ValueError:
        pass
    else:
        raise AssertionError("agent's own claim was used as success")
    r.verifier_said = True
    r.ground_truth = False
    assert r.verified_success() is False


def test_infra_failures_excluded_from_rates():
    runs = [
        {"condition": "A", "task_id": "T1", "verified_success": True, "infra_failure": False},
        {"condition": "A", "task_id": "T1", "verified_success": False, "infra_failure": True},
    ]
    assert trace.group_by_task(runs, "A") == {"T1": [True]}
    assert trace.infra_failure_rate(runs) == 0.5


# ---------------------------------------------------------------------- kb

def _finding(**kw):
    base = dict(
        id="LE-KB", hypothesis="X improves pass^5 over Y", preregistration="p.yaml",
        conditions=["A", "B"], tasks={"public": [], "private_holdout_n": 40},
        models=["qwen/qwen3"], n_runs=400, k_reruns=5,
        primary_metric="verified_success_pass_k",
        effect_size={"value": 0.1, "ci_low": 0.02, "ci_high": 0.18},
        false_accept_rate=0.05, false_reject_rate=0.03,
        cost={"usd": 1.0, "gpu_hours": 0, "wallclock": 1.0},
        confounds_checked=["equal_tokens"], skeptic_attempts=[], status="SUPPORTED",
        scope_limits="holds on holdout only", unexplained="residual variance by task family",
        causal_verdict="CAUSAL_ELIGIBLE",
    )
    base.update(kw)
    return kb.Finding(**base)


def test_supported_requires_causal_eligible():
    try:
        _finding(status="SUPPORTED", causal_verdict="CORRELATIONAL")
    except kb.SchemaViolation:
        pass
    else:
        raise AssertionError("SUPPORTED finding was accepted despite failed confounds (CORRELATIONAL)")


def test_placeholder_effect_blocks_supported_finding():
    try:
        _finding(status="SUPPORTED", effect_size={"value": 0.5, "ci_low": 0.2, "ci_high": 0.8, "is_placeholder": True})
    except kb.SchemaViolation:
        return
    raise AssertionError("Finding with is_placeholder=True was allowed to be created")


def test_unexplained_is_mandatory():
    try:
        _finding(unexplained="   ")
    except kb.SchemaViolation:
        return
    raise AssertionError("empty 'unexplained' was accepted")


def test_hedging_language_rejected():
    try:
        _finding(scope_limits="promising on short tasks")
    except kb.SchemaViolation:
        return
    raise AssertionError("hedging language was accepted")


def test_principle_requires_signoff_and_two_families():
    f = _finding(causal_verdict="CAUSAL_ELIGIBLE", replications=["LE-KB-R1"])
    assert not f.is_principle_eligible()[0]
    f.models = ["qwen/qwen3", "deepseek/v3"]
    assert not f.is_principle_eligible()[0], "machine declared a principle without a human"
    f.human_signoff = True
    assert f.is_principle_eligible()[0]


def test_settled_hypothesis_blocks_rerun():
    tmp = tempfile.mkdtemp()
    try:
        f = _finding(status="REFUTED")
        f.save(tmp)
        assert kb.already_settled(f.hypothesis, tmp) is not None
        assert kb.already_settled("a completely different question", tmp) is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# -------------------------------------------------------------- regression

def test_regression_detection():
    b_tasks = {"T1": [True, True], "T2": [False, False]}
    t_tasks = {"T1": [False, False], "T2": [True, True], "T3": [True, True]}
    report = check_regression(b_tasks, t_tasks)
    assert report.has_regression is True
    assert len(report.regressed_tasks) == 1
    assert report.regressed_tasks[0].task_id == "T1"
    assert report.verdict == "IMPROVED_WITH_REGRESSION"
    assert abs(report.net_improvement - (2/3 - 1/2)) < 1e-6


def test_regression_clean_improvement():
    b_tasks = {"T1": [True, True], "T2": [False, False]}
    t_tasks = {"T1": [True, True], "T2": [True, True]}
    report = check_regression(b_tasks, t_tasks)
    assert report.has_regression is False
    assert len(report.regressed_tasks) == 0
    assert report.verdict == "CLEAN_IMPROVEMENT"
    assert report.net_improvement == 0.5


def test_regression_empty_inputs():
    report = check_regression({}, {})
    assert report.verdict == "NO_MEANINGFUL_CHANGE"
    assert report.has_regression is False


# -------------------------------------------------------------- controller

def test_controller_control_halts_after_one_attempt():
    from lerm.controller import DeterministicLoopController, LoopCondition, LoopStep
    ctrl = DeterministicLoopController(LoopCondition.CONTROL)
    assert ctrl.decide_next_step(None) == "initial_attempt"
    step1 = LoopStep(0, "initial_attempt", "m", in_loop_passed=False)
    ctrl.record_step(step1)
    assert ctrl.decide_next_step(step1) == "halt"


def test_controller_retry_restarts_on_failure():
    from lerm.controller import DeterministicLoopController, LoopCondition, LoopStep
    ctrl = DeterministicLoopController(LoopCondition.RETRY)
    step1 = LoopStep(0, "initial_attempt", "m", in_loop_passed=False)
    ctrl.record_step(step1)
    assert ctrl.decide_next_step(step1) == "retry"


def test_controller_verify_repairs_on_failure():
    from lerm.controller import DeterministicLoopController, LoopCondition, LoopStep
    ctrl = DeterministicLoopController(LoopCondition.VERIFY)
    step1 = LoopStep(0, "initial_attempt", "m", in_loop_passed=False)
    ctrl.record_step(step1)
    assert ctrl.decide_next_step(step1) == "repair"
    # Success halts
    step2 = LoopStep(1, "repair", "m", in_loop_passed=True)
    ctrl.record_step(step2)
    assert ctrl.decide_next_step(step2) == "halt"


def test_controller_enforces_token_and_turn_budget():
    from lerm.controller import DeterministicLoopController, LoopCondition, LoopStep, EpisodeBudget
    budget = EpisodeBudget(max_tokens=1000, max_turns=2)
    ctrl = DeterministicLoopController(LoopCondition.VERIFY, budget=budget)
    step1 = LoopStep(0, "initial_attempt", "m", in_loop_passed=False, tokens_consumed=1200)
    ctrl.record_step(step1)
    assert ctrl.is_budget_exhausted() is True
    assert ctrl.decide_next_step(step1) == "halt"


def test_skeptic_rejects_placeholder_effect():
    from lerm.skeptic import Skeptic, KILL
    from lerm.stats import Effect
    sk = Skeptic(skeptic_model="deepseek/deepseek-v3", model_under_test="ollama/qwen2.5-coder:1.5b")
    placeholder_effect = Effect(value=0.5, ci_low=0.1, ci_high=0.9, n_tasks=1, k=5, method="placeholder", is_placeholder=True)
    res = sk.attack_noise(placeholder_effect, threshold=0.05)
    assert res.status == KILL
    assert "placeholder" in res.detail


def test_wilson_score_interval():
    from lerm.stats import wilson_score_interval, clopper_pearson_interval
    # At p_hat = 0.5 with n = 20
    w_low, w_high = wilson_score_interval(10, 20, alpha=0.05)
    assert 0.29 < w_low < 0.31
    assert 0.69 < w_high < 0.71
    
    # Boundary p_hat = 0
    w0_low, w0_high = wilson_score_interval(0, 20, alpha=0.05)
    assert w0_low == 0.0
    assert w0_high < 0.17

    # Clopper-Pearson comparison
    cp_low, cp_high = clopper_pearson_interval(10, 20, alpha=0.05)
    assert cp_low < w_low  # Clopper-Pearson is strictly wider/more conservative
    assert cp_high > w_high


def test_calibration_sample_size():
    from lerm.stats import calibration_sample_size, evaluate_calibration_admission
    n = calibration_sample_size(target_margin=0.15, alpha=0.05, p_assumed=0.50)
    assert n == 43
    
    # Admission tests at n=20
    dec, _ = evaluate_calibration_admission(10, 20)  # 50%
    assert dec == "ADMIT"
    
    dec_easy, _ = evaluate_calibration_admission(19, 20)  # 95%
    assert dec_easy == "REJECT_TOO_EASY"

    dec_hard, _ = evaluate_calibration_admission(2, 20)  # 10%
    assert dec_hard == "REJECT_TOO_HARD"


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
