"""Independent Repairability Classifier for LERM (Gates A6 & A7).

CRITICAL CAUSAL PRINCIPLE:
Repairability MUST NEVER be established by running `loop_verify` or measuring
Turn-2 recovery under the experimental treatment. Doing so introduces circularity
and post-treatment selection bias into EXP-LOOP-003.

Instead, repairability is defined by structural and diagnostic properties
observable from the initial single-shot failure trace and reference ground-truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class RepairabilityClass:
    REPAIRABLE = "REPAIRABLE"
    UNREPAIRABLE = "UNREPAIRABLE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    AMBIGUOUS = "AMBIGUOUS"
    EVALUATOR_FAILURE = "EVALUATOR_FAILURE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FailureClassification:
    classification: str
    is_repairable: bool
    reason: str
    diagnostic_details: dict[str, Any]


def classify_failure(
    trace_record: Mapping[str, Any],
    has_valid_reference_patch: bool,
    traceback_text: str = "",
    exit_code: int = 1,
    timeout_occurred: bool = False,
    test_flaky: bool = False,
) -> FailureClassification:
    """Classifies an initial single-shot failure INDEPENDENTLY of loop_verify.

    Invariants:
      - Never inspects loop_verify outcomes or Turn-2 actions.
      - Flags infrastructure failures (OOM, timeout, container crashes).
      - Flags ambiguous evaluator behaviors (flaky tests).
      - Requires a valid reference patch to confirm the defect is solvable.
    """
    # 1. Infrastructure failures
    if trace_record.get("infra_failure") or timeout_occurred:
        return FailureClassification(
            classification=RepairabilityClass.INFRASTRUCTURE,
            is_repairable=False,
            reason="Trial terminated due to infrastructure crash, timeout, or container fault.",
            diagnostic_details={"infra_failure": True, "timeout": timeout_occurred},
        )

    # 2. Ambiguous evaluator / flakiness
    if test_flaky:
        return FailureClassification(
            classification=RepairabilityClass.AMBIGUOUS,
            is_repairable=False,
            reason="Ground truth evaluator exhibits non-deterministic or flaky behavior.",
            diagnostic_details={"test_flaky": True},
        )

    # 3. Evaluator failure (e.g. syntax error in test file or harness crash)
    tb_lower = traceback_text.lower()
    if "syntaxerror" in tb_lower and ("test_" in tb_lower or "conftest" in tb_lower):
        return FailureClassification(
            classification=RepairabilityClass.EVALUATOR_FAILURE,
            is_repairable=False,
            reason="Ground-truth test suite itself has a syntax or import error.",
            diagnostic_details={"evaluator_error": True},
        )

    # 4. Solvability check: Must have a proven reference patch
    if not has_valid_reference_patch:
        return FailureClassification(
            classification=RepairabilityClass.UNREPAIRABLE,
            is_repairable=False,
            reason="No known valid reference patch exists to satisfy the ground-truth checker.",
            diagnostic_details={"has_reference_patch": False},
        )

    # 5. Localized diagnostic signal check
    # Traceback must contain specific assertion or exception details from the target code
    has_diagnostic_signal = any(
        err in tb_lower
        for err in [
            "assertionerror",
            "attributeerror",
            "typeerror",
            "valueerror",
            "keyerror",
            "indexerror",
            "failed",
        ]
    )
    if not has_diagnostic_signal:
        return FailureClassification(
            classification=RepairabilityClass.UNREPAIRABLE,
            is_repairable=False,
            reason="Failure produced no diagnostic error or stacktrace in target code.",
            diagnostic_details={"has_diagnostic_signal": False},
        )

    # Localized, diagnostic, solvable defect
    return FailureClassification(
        classification=RepairabilityClass.REPAIRABLE,
        is_repairable=True,
        reason="Failure is localized, solvable by known reference patch, and provides informative diagnostic traceback.",
        diagnostic_details={
            "has_reference_patch": True,
            "has_diagnostic_signal": True,
            "infra_ok": True,
        },
    )
