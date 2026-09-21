"""Deterministic Loop Controller for LERM Experiments.

Implements the three core experimental arms:
- Condition 0 ('control'): Single-pass execution (no iterative loop)
- Condition 1 ('loop_retry'): Compute-matched naive retry (restart on failure)
- Condition 2 ('loop_verify'): In-loop verification and targeted repair
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from lerm.trace import RunRecord


class LoopCondition(str, Enum):
    CONTROL = "control"
    RETRY = "loop_retry"
    VERIFY = "loop_verify"


@dataclass
class EpisodeBudget:
    max_wallclock_s: float = 120.0
    max_tokens: int = 16000
    max_turns: int = 4


@dataclass
class LoopStep:
    turn_index: int
    action_kind: str          # "initial_attempt" | "verify" | "repair" | "retry" | "halt"
    model_id: str
    in_loop_passed: bool | None = None
    ground_truth_passed: bool | None = None
    tokens_consumed: int = 0
    duration_s: float = 0.0
    diagnostic_info: str = ""


class DeterministicLoopController:
    """Orchestrates loop iterations and enforces matched budget constraints."""

    def __init__(self, condition: LoopCondition | str, budget: EpisodeBudget | None = None) -> None:
        self.condition = LoopCondition(condition)
        self.budget = budget or EpisodeBudget()
        self.steps: list[LoopStep] = []
        self.t0 = time.time()
        self.accumulated_tokens = 0

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.t0

    def remaining_wallclock_s(self) -> float:
        """Returns the remaining wallclock seconds in this episode budget."""
        return max(0.0, self.budget.max_wallclock_s - self.elapsed_s)

    def is_budget_exhausted(self) -> bool:
        if self.elapsed_s >= self.budget.max_wallclock_s:
            return True
        if self.accumulated_tokens >= self.budget.max_tokens:
            return True
        if len(self.steps) >= self.budget.max_turns:
            return True
        return False

    def decide_next_step(self, last_step: LoopStep | None) -> str:
        """Determines the next action primitive according to condition policy."""
        if last_step is None:
            return "initial_attempt"

        # Check budget ceiling
        if self.is_budget_exhausted():
            return "halt"

        # If in-loop verifier says pass or ground-truth passes, we halt
        if last_step.in_loop_passed is True:
            return "halt"

        # Condition 0: Control -> never loops
        if self.condition == LoopCondition.CONTROL:
            return "halt"

        # Condition 1: Naive Retry -> restarts trial
        if self.condition == LoopCondition.RETRY:
            if len(self.steps) < self.budget.max_turns:
                return "retry"
            return "halt"

        # Condition 2: Verification Loop -> diagnoses and attempts repair
        if self.condition == LoopCondition.VERIFY:
            if last_step.in_loop_passed is False and len(self.steps) < self.budget.max_turns:
                return "repair"
            return "halt"

        return "halt"

    def record_step(self, step: LoopStep) -> None:
        self.steps.append(step)
        self.accumulated_tokens += step.tokens_consumed
