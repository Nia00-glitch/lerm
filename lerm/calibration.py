"""Phase D Difficulty Calibration Evaluation and Manifest Management (Protocol 06 & DECISION-0006).

Governs Stage 1 Sequential Screening (N1 = 10), Stage 2 Precision Evaluation (N = 20),
admission threshold gating, rejection logging, and manifest freezing.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from typing import Any, Mapping, Sequence

from lerm.stats import wilson_score_interval
from lerm.trace_purity import audit_calibration_trace, verify_calibration_cohort_purity


def evaluate_stage1_screen(successes: int, n: int = 10) -> str:
    """Evaluates Stage 1 preliminary screening per Protocol 06 §2.

    Rule:
      - X1 <= 1: REJECT_FLOOR
      - X1 >= 9: REJECT_CEILING
      - 2 <= X1 <= 8: CONTINUE_TO_STAGE_2
    """
    if n != 10:
        raise ValueError(f"Stage 1 requires exactly n=10 trials, got {n}")
    if not (0 <= successes <= n):
        raise ValueError(f"successes must be in [0, {n}], got {successes}")

    if successes <= 1:
        return "REJECT_FLOOR"
    if successes >= 9:
        return "REJECT_CEILING"
    return "CONTINUE_TO_STAGE_2"


def evaluate_stage2_admission(
    total_successes: int,
    total_n: int = 20,
    alpha: float = 0.05,
) -> tuple[str, float, tuple[float, float]]:
    """Evaluates Stage 2 full precision admission per Protocol 06 §2 & DECISION-0006.

    Rule:
      - Total trials N = 20
      - Point estimate: 0.35 <= p_hat <= 0.65 (7 <= X <= 13)
      - 95% Wilson CI must intersect [0.30, 0.70]
    """
    if total_n != 20:
        raise ValueError(f"Stage 2 requires exactly total_n=20 trials, got {total_n}")
    if not (0 <= total_successes <= total_n):
        raise ValueError(f"total_successes must be in [0, {total_n}], got {total_successes}")

    p_hat = total_successes / total_n
    ci = wilson_score_interval(total_successes, total_n, alpha=alpha)
    ci_intersects = not (ci[1] < 0.30 or ci[0] > 0.70)

    if 7 <= total_successes <= 13 and ci_intersects:
        decision = "ADMIT"
    elif total_successes < 7:
        decision = "REJECT_OUT_OF_BAND_HARD"
    else:
        decision = "REJECT_OUT_OF_BAND_EASY"

    return decision, p_hat, ci


def compute_task_metrics(traces: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Computes comprehensive calibration metrics from a list of trace records."""
    if not traces:
        raise ValueError("traces sequence must not be empty")

    n_trials = len(traces)
    successes = sum(1 for t in traces if t.get("success", False))
    p_hat = round(successes / n_trials, 4)
    ci_raw = wilson_score_interval(successes, n_trials)
    wilson_ci = [round(ci_raw[0], 4), round(ci_raw[1], 4)]

    durations = [float(t.get("duration_s", 0.0)) for t in traces]
    actions = [int(t.get("actions_taken", 0)) for t in traces]
    mean_duration = round(sum(durations) / len(durations), 2) if durations else 0.0
    mean_actions = round(sum(actions) / len(actions), 2) if actions else 0.0

    metrics: dict[str, Any] = {
        "n_trials": n_trials,
        "successes": successes,
        "p_hat": p_hat,
        "wilson_ci_95": wilson_ci,
        "mean_duration_s": mean_duration,
        "mean_actions_taken": mean_actions,
    }

    if n_trials >= 10:
        s1_succ = sum(1 for t in traces[:10] if t.get("success", False))
        metrics["stage1_verdict"] = evaluate_stage1_screen(s1_succ, 10)
        metrics["stage1_successes"] = s1_succ
    else:
        metrics["stage1_verdict"] = "STAGE_1_IN_PROGRESS"

    if n_trials == 20:
        decision, _, _ = evaluate_stage2_admission(successes, 20)
        metrics["stage2_verdict"] = decision
        metrics["overall_verdict"] = decision
        metrics["target_band_membership"] = (decision == "ADMIT")
    elif metrics.get("stage1_verdict") in ("REJECT_FLOOR", "REJECT_CEILING"):
        metrics["overall_verdict"] = metrics["stage1_verdict"]
        metrics["target_band_membership"] = False
    elif n_trials >= 10:
        metrics["overall_verdict"] = "STAGE_2_IN_PROGRESS"
        metrics["target_band_membership"] = (0.35 <= p_hat <= 0.65)
    else:
        metrics["overall_verdict"] = "STAGE_1_IN_PROGRESS"
        metrics["target_band_membership"] = None

    return metrics


def generate_admitted_manifest_yaml(
    admitted_tasks: list[dict[str, Any]],
    model_name: str,
) -> str:
    """Generates the frozen YAML manifest content for admitted primary tasks."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    lines = [
        'schema_version: "2.0.0"',
        'manifest_id: "EXP-LOOP-003-ADMITTED-PRIMARY"',
        f'calibrated_at: "{now_iso}"',
        f'calibration_model: "{model_name}"',
        f'total_admitted: {len(admitted_tasks)}',
        'tasks:',
    ]
    for t in admitted_tasks:
        lines.append(f'  - id: "{t["id"]}"')
        if "constituent_tasks" in t:
            lines.append("    constituent_tasks:")
            for ct in t["constituent_tasks"]:
                lines.append(f'      - "{ct}"')
        if "constituent_functions" in t:
            lines.append("    constituent_functions:")
            for cf in t["constituent_functions"]:
                lines.append(f'      - "{cf}"')
        if "constituent_rules" in t:
            lines.append("    constituent_rules:")
            for cr in t["constituent_rules"]:
                lines.append(f'      - "{cr}"')
        lines.append(f'    patch_path: "{t.get("patch_path", "")}"')
        lines.append(f'    patch_hash: "{t.get("patch_hash", "")}"')
        lines.append(f'    p_hat: {t.get("p_hat", 0.0)}')
        lines.append(f'    wilson_ci_95: {json.dumps(t.get("wilson_ci_95", []))}')
        lines.append('    data_role: "primary"')
        lines.append('    primary_exp_loop_003_eligible: true')

    return "\n".join(lines) + "\n"
