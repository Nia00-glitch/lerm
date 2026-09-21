"""Unit tests for the Independent Repairability Classifier (Gate A7).

Validates that the classifier accurately distinguishes:
  1. Known repairable failures
  2. Known unrepairable failures
  3. Infrastructure failures
  4. Ambiguous / flaky evaluator failures
  5. Evaluator code / syntax errors
without ever inspecting loop_verify or Turn-2 treatment mechanisms.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm.repairability import classify_failure, RepairabilityClass


class TestRepairabilityClassifier(unittest.TestCase):
    def test_known_repairable(self):
        trace = {"run_id": "cal-001", "infra_failure": False}
        tb = "AssertionError: Expected 5, got 0\n  File 'app/calc.py', line 12, in add"
        res = classify_failure(
            trace_record=trace,
            has_valid_reference_patch=True,
            traceback_text=tb,
            exit_code=1,
        )
        self.assertEqual(res.classification, RepairabilityClass.REPAIRABLE)
        self.assertTrue(res.is_repairable)

    def test_known_unrepairable_no_reference_patch(self):
        trace = {"run_id": "cal-002", "infra_failure": False}
        tb = "AssertionError: Target output mismatch"
        res = classify_failure(
            trace_record=trace,
            has_valid_reference_patch=False,
            traceback_text=tb,
            exit_code=1,
        )
        self.assertEqual(res.classification, RepairabilityClass.UNREPAIRABLE)
        self.assertFalse(res.is_repairable)

    def test_known_unrepairable_no_diagnostic_signal(self):
        trace = {"run_id": "cal-003", "infra_failure": False}
        tb = "Process killed with silent exit code 1"
        res = classify_failure(
            trace_record=trace,
            has_valid_reference_patch=True,
            traceback_text=tb,
            exit_code=1,
        )
        self.assertEqual(res.classification, RepairabilityClass.UNREPAIRABLE)
        self.assertFalse(res.is_repairable)

    def test_infra_failure_flagged(self):
        trace = {"run_id": "cal-004", "infra_failure": True}
        res = classify_failure(
            trace_record=trace,
            has_valid_reference_patch=True,
            traceback_text="OOMKilled",
            exit_code=137,
        )
        self.assertEqual(res.classification, RepairabilityClass.INFRASTRUCTURE)
        self.assertFalse(res.is_repairable)

    def test_timeout_flagged_as_infra(self):
        trace = {"run_id": "cal-005", "infra_failure": False}
        res = classify_failure(
            trace_record=trace,
            has_valid_reference_patch=True,
            traceback_text="Timeout after 120s",
            exit_code=124,
            timeout_occurred=True,
        )
        self.assertEqual(res.classification, RepairabilityClass.INFRASTRUCTURE)
        self.assertFalse(res.is_repairable)

    def test_ambiguous_flaky_evaluator(self):
        trace = {"run_id": "cal-006", "infra_failure": False}
        res = classify_failure(
            trace_record=trace,
            has_valid_reference_patch=True,
            traceback_text="AssertionError: random network glitch",
            exit_code=1,
            test_flaky=True,
        )
        self.assertEqual(res.classification, RepairabilityClass.AMBIGUOUS)
        self.assertFalse(res.is_repairable)

    def test_evaluator_syntax_failure(self):
        trace = {"run_id": "cal-007", "infra_failure": False}
        tb = "SyntaxError: invalid syntax in tests/test_calc.py, line 4"
        res = classify_failure(
            trace_record=trace,
            has_valid_reference_patch=True,
            traceback_text=tb,
            exit_code=1,
        )
        self.assertEqual(res.classification, RepairabilityClass.EVALUATOR_FAILURE)
        self.assertFalse(res.is_repairable)


if __name__ == "__main__":
    unittest.main()
