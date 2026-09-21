"""Regression checker for loop capabilities.

Distinguishes:
1. Genuine capability improvement (new capability improves, old capabilities hold).
2. Regressive improvement (new capability improves BUT previous capabilities regress).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Sequence, Any


@dataclass
class TaskDelta:
    task_id: str
    baseline_pass_rate: float
    treatment_pass_rate: float
    delta: float
    is_regression: bool


@dataclass
class RegressionReport:
    overall_baseline_rate: float
    overall_treatment_rate: float
    net_improvement: float
    regressed_tasks: list[TaskDelta]
    improved_tasks: list[TaskDelta]
    unchanged_tasks: list[TaskDelta]

    @property
    def has_regression(self) -> bool:
        return len(self.regressed_tasks) > 0

    @property
    def verdict(self) -> str:
        if self.net_improvement > 0 and self.has_regression:
            return "IMPROVED_WITH_REGRESSION"
        elif self.net_improvement > 0:
            return "CLEAN_IMPROVEMENT"
        elif self.has_regression:
            return "REGRESSION_DOMINATED"
        else:
            return "NO_MEANINGFUL_CHANGE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "overall_baseline_rate": self.overall_baseline_rate,
            "overall_treatment_rate": self.overall_treatment_rate,
            "net_improvement": self.net_improvement,
            "n_regressed_tasks": len(self.regressed_tasks),
            "regressed_tasks": [asdict(t) for t in self.regressed_tasks],
            "n_improved_tasks": len(self.improved_tasks),
            "improved_tasks": [asdict(t) for t in self.improved_tasks],
        }


def check_regression(
    baseline_by_task: dict[str, list[bool]],
    treatment_by_task: dict[str, list[bool]],
    regression_tolerance: float = 0.0,
) -> RegressionReport:
    regressed = []
    improved = []
    unchanged = []

    all_tasks = sorted(set(baseline_by_task.keys()) | set(treatment_by_task.keys()))
    base_all: list[bool] = []
    treat_all: list[bool] = []

    for tid in all_tasks:
        b_runs = baseline_by_task.get(tid, [])
        t_runs = treatment_by_task.get(tid, [])
        base_all.extend(b_runs)
        treat_all.extend(t_runs)

        b_rate = float(sum(b_runs) / len(b_runs)) if b_runs else 0.0
        t_rate = float(sum(t_runs) / len(t_runs)) if t_runs else 0.0
        diff = t_rate - b_rate

        td = TaskDelta(
            task_id=tid,
            baseline_pass_rate=b_rate,
            treatment_pass_rate=t_rate,
            delta=diff,
            is_regression=diff < -regression_tolerance,
        )
        if diff < -regression_tolerance:
            regressed.append(td)
        elif diff > regression_tolerance:
            improved.append(td)
        else:
            unchanged.append(td)

    base_avg = float(sum(base_all) / len(base_all)) if base_all else 0.0
    treat_avg = float(sum(treat_all) / len(treat_all)) if treat_all else 0.0

    return RegressionReport(
        overall_baseline_rate=base_avg,
        overall_treatment_rate=treat_avg,
        net_improvement=treat_avg - base_avg,
        regressed_tasks=regressed,
        improved_tasks=improved,
        unchanged_tasks=unchanged,
    )
