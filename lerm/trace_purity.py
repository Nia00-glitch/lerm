"""Calibration Trace Purity Validator (Gate A12)."""

from typing import Any, Mapping


class TracePurityViolation(RuntimeError):
    """Raised when a calibration trace contains loop feedback or multiple turns."""


def audit_calibration_trace(record: Mapping[str, Any]) -> list[str]:
    """Audits a single calibration trial for absolute purity."""
    errors = []
    if record.get("condition") != "single_shot_calibration":
        errors.append(
            f"condition must be 'single_shot_calibration', got '{record.get('condition')}'"
        )
    if record.get("attempts", 1) != 1:
        errors.append(f"attempts must be exactly 1, got {record.get('attempts')}")
    if record.get("turns_taken", 1) > 1:
        errors.append(
            f"turns_taken must be <= 1, got {record.get('turns_taken')}"
        )
    if record.get("verifier_calls", 0) != 0:
        errors.append(
            f"verifier_calls must be 0, got {record.get('verifier_calls')}"
        )
    if record.get("feedback_injected", False) is not False:
        errors.append(
            f"feedback_injected must be False, got {record.get('feedback_injected')}"
        )
    if record.get("retry_count", 0) != 0:
        errors.append(
            f"retry_count must be 0, got {record.get('retry_count')}"
        )
    return errors


def verify_calibration_cohort_purity(records: list[Mapping[str, Any]]) -> None:
    """Audits an entire cohort of calibration traces."""
    for r in records:
        errs = audit_calibration_trace(r)
        if errs:
            raise TracePurityViolation(
                f"Contaminated calibration record '{r.get('run_id')}': {'; '.join(errs)}"
            )
