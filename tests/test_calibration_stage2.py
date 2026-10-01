"""Unit and regression tests for Phase D Stage 1 / Stage 2 calibration logic."""

from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm.calibration import (
    evaluate_stage1_screen,
    evaluate_stage2_admission,
    compute_task_metrics,
    generate_admitted_manifest_yaml,
)
from lerm.trace_purity import audit_calibration_trace, verify_calibration_cohort_purity, TracePurityViolation


def test_stage1_screen_floor():
    assert evaluate_stage1_screen(0, 10) == "REJECT_FLOOR"
    assert evaluate_stage1_screen(1, 10) == "REJECT_FLOOR"


def test_stage1_screen_ceiling():
    assert evaluate_stage1_screen(9, 10) == "REJECT_CEILING"
    assert evaluate_stage1_screen(10, 10) == "REJECT_CEILING"


def test_stage1_screen_continue():
    for x in range(2, 9):
        assert evaluate_stage1_screen(x, 10) == "CONTINUE_TO_STAGE_2"


def test_stage1_screen_invalid_args():
    with pytest.raises(ValueError, match="Stage 1 requires exactly n=10"):
        evaluate_stage1_screen(5, 9)
    with pytest.raises(ValueError, match="successes must be in"):
        evaluate_stage1_screen(11, 10)
    with pytest.raises(ValueError, match="successes must be in"):
        evaluate_stage1_screen(-1, 10)


def test_stage2_admission_in_band():
    for x in range(7, 14):
        decision, p_hat, ci = evaluate_stage2_admission(x, 20)
        assert decision == "ADMIT"
        assert 0.35 <= p_hat <= 0.65
        assert not (ci[1] < 0.30 or ci[0] > 0.70)


def test_stage2_admission_out_of_band_hard():
    for x in range(0, 7):
        decision, p_hat, _ = evaluate_stage2_admission(x, 20)
        assert decision == "REJECT_OUT_OF_BAND_HARD"
        assert p_hat < 0.35


def test_stage2_admission_out_of_band_easy():
    for x in range(14, 21):
        decision, p_hat, _ = evaluate_stage2_admission(x, 20)
        assert decision == "REJECT_OUT_OF_BAND_EASY"
        assert p_hat > 0.65


def test_stage2_invalid_args():
    with pytest.raises(ValueError, match="total_n=20"):
        evaluate_stage2_admission(10, 15)
    with pytest.raises(ValueError, match="total_successes must be in"):
        evaluate_stage2_admission(21, 20)


def test_compute_task_metrics_stage1():
    # 6 successes out of 10
    traces = [
        {"success": (i < 6), "duration_s": 100.0 + i, "actions_taken": 10}
        for i in range(10)
    ]
    m = compute_task_metrics(traces)
    assert m["n_trials"] == 10
    assert m["successes"] == 6
    assert m["p_hat"] == 0.6
    assert m["stage1_verdict"] == "CONTINUE_TO_STAGE_2"
    assert m["stage1_successes"] == 6
    assert m["overall_verdict"] == "STAGE_2_IN_PROGRESS"


def test_compute_task_metrics_stage2_admit():
    # 6 successes in Stage 1, 5 successes in Stage 2 (11/20 total)
    traces = []
    for i in range(20):
        # Stage 1: i in 0..9 -> 6 True, 4 False
        # Stage 2: i in 10..19 -> 5 True, 5 False
        is_succ = (i < 6) if i < 10 else (i < 15)
        traces.append({"success": is_succ, "duration_s": 120.0, "actions_taken": 8})

    m = compute_task_metrics(traces)
    assert m["n_trials"] == 20
    assert m["successes"] == 11
    assert m["p_hat"] == 0.55
    assert m["stage1_verdict"] == "CONTINUE_TO_STAGE_2"
    assert m["stage1_successes"] == 6
    assert m["stage2_verdict"] == "ADMIT"
    assert m["overall_verdict"] == "ADMIT"
    assert m["target_band_membership"] is True


def test_gate_a12_trace_purity_adversarial():
    clean_trace = {
        "run_id": "CALIB-OH-COMP-001-t00-s61421",
        "condition": "single_shot_calibration",
        "data_role": "calibration",
        "attempts": 1,
        "turns_taken": 1,
        "verifier_calls": 0,
        "feedback_injected": False,
        "retry_count": 0,
    }
    assert audit_calibration_trace(clean_trace) == []

    # Inject verifier leak
    dirty_trace = dict(clean_trace, verifier_calls=1)
    errs = audit_calibration_trace(dirty_trace)
    assert len(errs) == 1
    assert "verifier_calls must be 0" in errs[0]

    with pytest.raises(TracePurityViolation):
        verify_calibration_cohort_purity([clean_trace, dirty_trace])


def test_format_admitted_manifest_yaml():
    tasks = [
        {
            "id": "COMP-001",
            "constituent_tasks": ["CAND-001", "CAND-003"],
            "constituent_functions": ["setdefault", "__init__"],
            "constituent_rules": ["func_pm_remove_assign", "func_pm_ctrl_invert_if"],
            "patch_path": "data/phase-d/patches/COMP-001.diff",
            "patch_hash": "abc123",
            "p_hat": 0.55,
            "wilson_ci_95": [0.34, 0.74],
        }
    ]
    yaml_text = generate_admitted_manifest_yaml(tasks, "openrouter/thinkingmachines/inkling-small:free")
    assert 'manifest_id: "EXP-LOOP-003-ADMITTED-PRIMARY"' in yaml_text
    assert 'total_admitted: 1' in yaml_text
    assert 'id: "COMP-001"' in yaml_text
    assert 'primary_exp_loop_003_eligible: true' in yaml_text
