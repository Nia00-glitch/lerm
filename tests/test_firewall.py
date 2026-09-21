"""Comprehensive Unit and Regression Tests for LERM Data Firewall (Phase B Remediation)."""

import os
import sys
import unittest
from pathlib import Path
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm.firewall import (
    verify_manifest_admission,
    verify_dataset_separation,
    verify_manifest,
    validate_task_identity,
    FirewallViolation,
    HISTORICAL_TASK_REGISTRY,
)


class TestDataFirewallRemediated(unittest.TestCase):
    def setUp(self):
        self.clean_candidate = {
            "id": "SWE-SM-001",
            "data_role": "primary",
            "historical_exposure": False,
            "primary_exp_loop_003_eligible": True,
            "provenance": {
                "repository": "mewwts__addict.75284f95",
                "commit": "affe22e",
                "mutation": "func_pm_ctrl_invert_if",
            },
            "setup": {
                "files": [{"path": "addict/addict.py", "content": "def test(): pass\n"}]
            },
        }

    # 1. Historical -> primary rejected
    def test_historical_primary_rejected(self):
        for tid in ["HOLDOUT-001", "HOLDOUT-002", "HOLDOUT-003", "HOLDOUT-004"]:
            path = Path(f"holdout/tasks/{tid}.yaml")
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            with self.assertRaises(FirewallViolation) as ctx:
                verify_manifest_admission(data, target_role="primary")
            self.assertIn("REJECTED", str(ctx.exception))
            self.assertIn("historical_exposure=True", str(ctx.exception))

    # 2. Historical -> calibration rejected
    def test_historical_calibration_rejected(self):
        for tid in ["HOLDOUT-001", "HOLDOUT-002", "HOLDOUT-003", "HOLDOUT-004"]:
            path = Path(f"holdout/tasks/{tid}.yaml")
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            with self.assertRaises(FirewallViolation) as ctx:
                verify_manifest_admission(data, target_role="calibration")
            self.assertIn("REJECTED", str(ctx.exception))
            self.assertIn("cannot enter EXP-LOOP-003 calibration", str(ctx.exception))

    # 3. Historical trace rejected
    def test_historical_trace_rejected(self):
        trace = [
            {"run_id": "r1", "task_id": "HOLDOUT-001", "data_role": "primary"}
        ]
        with self.assertRaises(FirewallViolation) as ctx:
            verify_dataset_separation(trace, expected_role="primary")
        self.assertIn("Historical task 'HOLDOUT-001' detected", str(ctx.exception))

    # 4. Both flags tampered rejected
    def test_both_flags_tampered_rejected(self):
        tampered = {
            "id": "HOLDOUT-001",
            "historical_exposure": False,
            "primary_exp_loop_003_eligible": True,
            "provenance": {"repo": "fake"},
        }
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(tampered, target_role="primary")
        self.assertIn("Metadata tampering detected", str(ctx.exception))

    # 5. Copied historical fixture rejected
    def test_copied_historical_fixture_rejected(self):
        holdout_path = Path("holdout/tasks/HOLDOUT-001.yaml")
        with open(holdout_path, "r", encoding="utf-8") as f:
            holdout_data = yaml.safe_load(f)
        copied_task = {
            "id": "FAKE-FRESH-001",
            "historical_exposure": False,
            "primary_exp_loop_003_eligible": True,
            "provenance": {"repo": "copy"},
            "setup": holdout_data["setup"],
        }
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(copied_task, target_role="primary")
        self.assertIn("Copied historical artifact detected", str(ctx.exception))
        self.assertIn("HOLDOUT-001", str(ctx.exception))

    # 6. Bare historical manifest rejected
    def test_bare_historical_manifest_rejected(self):
        bare_manifest = ["HOLDOUT-001", "HOLDOUT-002"]
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest(bare_manifest, target_role="primary")
        self.assertIn("REJECTED: Manifest entry must be a mapping", str(ctx.exception))

    # 7. Missing historical flag rejected
    def test_missing_historical_flag_rejected(self):
        bad = dict(self.clean_candidate)
        del bad["historical_exposure"]
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(bad, target_role="primary")
        self.assertIn("missing 'historical_exposure' field", str(ctx.exception))

    # 8. Missing eligibility flag rejected
    def test_missing_eligibility_flag_rejected(self):
        bad = dict(self.clean_candidate)
        del bad["primary_exp_loop_003_eligible"]
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(bad, target_role="primary")
        self.assertIn("missing 'primary_exp_loop_003_eligible' field", str(ctx.exception))

    # 9. String boolean rejected
    def test_string_boolean_rejected(self):
        bad = dict(self.clean_candidate)
        bad["historical_exposure"] = "false"
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(bad, target_role="primary")
        self.assertIn("non-boolean historical_exposure='false'", str(ctx.exception))

        bad2 = dict(self.clean_candidate)
        bad2["primary_exp_loop_003_eligible"] = "true"
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(bad2, target_role="primary")
        self.assertIn("non-boolean primary_exp_loop_003_eligible='true'", str(ctx.exception))

    # 10. Unknown task ID without provenance rejected
    def test_unknown_task_id_rejected(self):
        unknown = {
            "id": "UNTRACKED-001",
            "historical_exposure": False,
            "primary_exp_loop_003_eligible": True,
        }
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(unknown, target_role="primary")
        self.assertIn("missing required provenance metadata", str(ctx.exception))

    # 11. Missing provenance rejected
    def test_missing_provenance_rejected(self):
        bad = dict(self.clean_candidate)
        del bad["provenance"]
        with self.assertRaises(FirewallViolation) as ctx:
            verify_manifest_admission(bad, target_role="primary")
        self.assertIn("missing required provenance metadata", str(ctx.exception))

    # 12. Hash mismatch / registry tampering rejected
    def test_hash_mismatch_rejected(self):
        tampered = {
            "id": "HOLDOUT-001",
            "historical_exposure": False,
            "primary_exp_loop_003_eligible": True,
            "provenance": {"source": "fake"},
        }
        with self.assertRaises(FirewallViolation) as ctx:
            validate_task_identity(tampered)
        self.assertIn("Metadata tampering detected on 'HOLDOUT-001'", str(ctx.exception))

    # 13. Fresh valid candidate admitted
    def test_fresh_valid_candidate_admitted(self):
        prov = verify_manifest_admission(self.clean_candidate, target_role="primary")
        self.assertEqual(prov.task_id, "SWE-SM-001")
        self.assertFalse(prov.is_historical)
        self.assertTrue(prov.is_eligible_primary)


if __name__ == "__main__":
    unittest.main()
