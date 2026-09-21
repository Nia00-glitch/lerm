"""Adversarial Attack Test Suite for LERM EXP-LOOP-003 Phase C.

Executes all 20 required adversarial attack vectors to prove the candidate-generation
and admission protocol fails closed against contamination, leaks, and invalid tasks:
 1. Historical task injected into calibration
 2. Historical task injected into primary
 3. Fresh task with fake provenance
 4. Fresh task with missing provenance
 5. Fresh task with altered provenance
 6. Candidate copied from historical fixture
 7. Candidate with one-byte source perturbation
 8. Duplicate mutation
 9. Same mutation under different ID
10. Treatment-success information injected into candidate metadata
11. Calibration result injected into generator state
12. Candidate with missing mutation ID
13. Candidate with mismatched repository/commit
14. Candidate with mismatched content hash
15. Candidate whose baseline already fails
16. Candidate whose mutation produces no semantic failure
17. Candidate whose failure is infrastructure-only
18. Candidate whose reference repair does not restore PASS
19. Candidate whose reset hash differs
20. Candidate generated with same seed twice
"""

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm.candidate_schema import CandidateTaskUnit, CandidateValidationError
from lerm.candidate_pool import CandidatePool, RejectionReason, TreatmentLeakageError
from lerm.firewall import FirewallViolation, HISTORICAL_FIXTURE_HASHES, HISTORICAL_TASK_REGISTRY, validate_task_identity


def compute_sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def make_valid_candidate(
    task_id="CAND-001",
    mutation_id="mut_001",
    mutation_seed=42,
    mutation_rule="func_pm_remove_cond",
    data_role="raw_candidate",
    patch="--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-x = 1\n+pass",
    prov=None,
    gen_config_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
) -> tuple[CandidateTaskUnit, str]:
    patch_hash = compute_sha256(patch)
    dummy_hash = "a" * 64
    prov = prov or {
        "generator_version": "swe-smith-9b74ac0",
        "generator_config_hash": gen_config_hash,
        "timestamp": "2026-09-21T12:00:00Z",
    }
    cand = CandidateTaskUnit(
        task_id=task_id,
        source_repository="mewwts__addict.75284f95",
        source_commit="75284f95",
        mutation_id=mutation_id,
        mutation_seed=mutation_seed,
        mutation_rule=mutation_rule,
        original_file_paths=("addict/addict.py",),
        mutated_file_paths=("addict/addict.py",),
        baseline_state_id=dummy_hash,
        mutated_state_id=dummy_hash,
        candidate_content_hash=patch_hash,
        baseline_content_hash=dummy_hash,
        generation_timestamp="2026-09-21T12:00:00Z",
        generator_version="swe-smith-9b74ac0",
        generator_config_hash=gen_config_hash,
        task_schema_version="1.0.0",
        data_role=data_role,
        historical_exposure=False,
        primary_exp_loop_003_eligible=False,
        provenance=prov,
    )
    return cand, patch


class TestCandidateAdversarialSuite(unittest.TestCase):

    def setUp(self):
        self.pool = CandidatePool()

    # 1. Historical task injected into calibration
    def test_01_historical_task_injected_into_calibration(self):
        cand, patch = make_valid_candidate(task_id="HOLDOUT-001", data_role="calibration")
        res = self.pool.register_candidate(cand, patch)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.HISTORICAL_FIREWALL_BREACH)

    # 2. Historical task injected into primary
    def test_02_historical_task_injected_into_primary(self):
        cand, patch = make_valid_candidate(task_id="HOLDOUT-002", data_role="primary")
        res = self.pool.register_candidate(cand, patch)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.HISTORICAL_FIREWALL_BREACH)

    # 3. Fresh task with fake provenance
    def test_03_fresh_task_fake_provenance(self):
        cand, patch = make_valid_candidate(task_id="CAND-003", prov={"generator": "fake_unknown"})
        res = self.pool.register_candidate(cand, patch)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.PROVENANCE_TAMPERED)

    # 4. Fresh task with missing provenance
    def test_04_fresh_task_missing_provenance(self):
        dummy_hash = "a" * 64
        with self.assertRaises(CandidateValidationError):
            CandidateTaskUnit(
                task_id="CAND-004",
                source_repository="mewwts__addict.75284f95",
                source_commit="75284f95",
                mutation_id="mut_004",
                mutation_seed=42,
                mutation_rule="func_pm_remove_cond",
                original_file_paths=("addict/addict.py",),
                mutated_file_paths=("addict/addict.py",),
                baseline_state_id=dummy_hash,
                mutated_state_id=dummy_hash,
                candidate_content_hash=compute_sha256("diff"),
                baseline_content_hash=dummy_hash,
                generation_timestamp="2026-09-21T12:00:00Z",
                generator_version="swe-smith-9b74ac0",
                generator_config_hash=dummy_hash,
                provenance={},
            ).validate()

    # 5. Fresh task with altered provenance
    def test_05_fresh_task_altered_provenance(self):
        prov = {
            "generator_version": "swe-smith-9b74ac0",
            "generator_config_hash": "b" * 64,  # altered
            "timestamp": "2026-09-21T12:00:00Z",
        }
        cand, patch = make_valid_candidate(
            task_id="CAND-005",
            prov=prov,
            gen_config_hash="a" * 64,
        )
        res = self.pool.register_candidate(cand, patch)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.PROVENANCE_TAMPERED)

    # 6. Candidate copied from historical fixture
    def test_06_candidate_copied_from_historical_fixture(self):
        # Using known historical fixture hash from registry
        hist_hash = list(HISTORICAL_FIXTURE_HASHES.keys())[0]
        cand, _ = make_valid_candidate(task_id="CAND-006")
        # Direct firewall rejection of copied fixture content
        task_data = {
            "id": "CAND-006",
            "historical_exposure": False,
            "primary_exp_loop_003_eligible": True,
            "setup": {
                "files": [
                    {"path": "app/calc.py", "content": "dummy"}
                ]
            },
            "provenance": {"source": "fake"}
        }
        # Mock compute_fixture_hash to return hist_hash
        import lerm.firewall as fw_mod
        orig_comp = fw_mod.compute_fixture_hash
        try:
            fw_mod.compute_fixture_hash = lambda td: hist_hash
            with self.assertRaises(FirewallViolation):
                validate_task_identity(task_data)
        finally:
            fw_mod.compute_fixture_hash = orig_comp

    # 7. Candidate with one-byte source perturbation
    def test_07_candidate_one_byte_perturbation(self):
        cand, patch = make_valid_candidate(task_id="CAND-007")
        perturbed_patch = patch + " "  # one byte added
        res = self.pool.register_candidate(cand, perturbed_patch)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.HASH_MISMATCH)

    # 8. Duplicate mutation
    def test_08_duplicate_mutation(self):
        cand1, patch1 = make_valid_candidate(task_id="CAND-008A", mutation_id="mut_same")
        cand2, patch2 = make_valid_candidate(task_id="CAND-008B", mutation_id="mut_same")
        res1 = self.pool.register_candidate(cand1, patch1)
        self.assertTrue(res1.admitted)
        res2 = self.pool.register_candidate(cand2, patch2)
        self.assertFalse(res2.admitted)
        self.assertEqual(res2.rejection_reason, RejectionReason.DUPLICATE_MUTATION)

    # 9. Same mutation under different ID
    def test_09_same_mutation_under_different_id(self):
        patch = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-identical\n+mutated"
        cand1, _ = make_valid_candidate(task_id="CAND-009A", mutation_id="mut_A", patch=patch)
        cand2, _ = make_valid_candidate(task_id="CAND-009B", mutation_id="mut_B", patch=patch)
        res1 = self.pool.register_candidate(cand1, patch)
        self.assertTrue(res1.admitted)
        res2 = self.pool.register_candidate(cand2, patch)
        self.assertFalse(res2.admitted)
        self.assertEqual(res2.rejection_reason, RejectionReason.DUPLICATE_DIFF)

    # 10. Treatment-success information injected into candidate metadata
    def test_10_treatment_success_injected_into_metadata(self):
        prov = {
            "generator_version": "swe-smith-9b74ac0",
            "generator_config_hash": "a" * 64,
            "timestamp": "2026-09-21T12:00:00Z",
            "treatment_success": True,  # leaked treatment outcome
        }
        cand, patch = make_valid_candidate(task_id="CAND-010", prov=prov, gen_config_hash="a" * 64)
        res = self.pool.register_candidate(cand, patch)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.TREATMENT_LEAKAGE)

    # 11. Calibration result injected into generator state
    def test_11_calibration_result_injected_into_generator(self):
        prov = {
            "generator_version": "swe-smith-9b74ac0",
            "generator_config_hash": "a" * 64,
            "timestamp": "2026-09-21T12:00:00Z",
            "calibration_score": 0.55,  # leaked calibration outcome
        }
        cand, patch = make_valid_candidate(task_id="CAND-011", prov=prov, gen_config_hash="a" * 64)
        res = self.pool.register_candidate(cand, patch)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.TREATMENT_LEAKAGE)

    # 12. Candidate with missing mutation ID
    def test_12_candidate_missing_mutation_id(self):
        cand, patch = make_valid_candidate(task_id="CAND-012", mutation_id="")
        with self.assertRaises(CandidateValidationError):
            cand.validate()
        res = self.pool.register_candidate(cand, patch)
        self.assertFalse(res.admitted)

    # 13. Candidate with mismatched repository/commit
    def test_13_candidate_mismatched_repository_commit(self):
        dummy_hash = "a" * 64
        with self.assertRaises(CandidateValidationError):
            CandidateTaskUnit(
                task_id="CAND-013",
                source_repository="mewwts__addict.75284f95",
                source_commit="INVALID_COMMIT_ZZZ!",
                mutation_id="mut_013",
                mutation_seed=42,
                mutation_rule="func_pm_remove_cond",
                original_file_paths=("addict/addict.py",),
                mutated_file_paths=("addict/addict.py",),
                baseline_state_id=dummy_hash,
                mutated_state_id=dummy_hash,
                candidate_content_hash=dummy_hash,
                baseline_content_hash=dummy_hash,
                generation_timestamp="2026-09-21T12:00:00Z",
                generator_version="swe-smith-9b74ac0",
                generator_config_hash=dummy_hash,
                provenance={"generator_version": "1", "generator_config_hash": dummy_hash, "timestamp": "now"},
            ).validate()

    # 14. Candidate with mismatched content hash
    def test_14_candidate_mismatched_content_hash(self):
        with self.assertRaises(CandidateValidationError):
            CandidateTaskUnit(
                task_id="CAND-014",
                source_repository="mewwts__addict.75284f95",
                source_commit="75284f95",
                mutation_id="mut_014",
                mutation_seed=42,
                mutation_rule="func_pm_remove_cond",
                original_file_paths=("addict/addict.py",),
                mutated_file_paths=("addict/addict.py",),
                baseline_state_id="a" * 64,
                mutated_state_id="a" * 64,
                candidate_content_hash="not_a_valid_64_char_hash",
                baseline_content_hash="a" * 64,
                generation_timestamp="2026-09-21T12:00:00Z",
                generator_version="swe-smith-9b74ac0",
                generator_config_hash="a" * 64,
                provenance={"generator_version": "1", "generator_config_hash": "a" * 64, "timestamp": "now"},
            ).validate()

    # 15. Candidate whose baseline already fails
    def test_15_candidate_baseline_already_fails(self):
        cand, patch = make_valid_candidate(task_id="CAND-015", mutation_id="mut_015")
        def mock_evaluator(stage, p):
            if stage == "baseline":
                return 1, "FAIL: Test assertion failed in baseline"
            return 0, "PASS"
        res = self.pool.register_candidate(cand, patch, chain_evaluator=mock_evaluator)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.BASELINE_FAILURE)

    # 16. Candidate whose mutation produces no semantic failure
    def test_16_candidate_mutation_produces_no_semantic_failure(self):
        cand, patch = make_valid_candidate(task_id="CAND-016", mutation_id="mut_016")
        def mock_evaluator(stage, p):
            if stage == "baseline":
                return 0, "PASS"
            if stage == "mutated":
                return 0, "PASS: All tests still pass (no semantic failure)"
            return 0, "PASS"
        res = self.pool.register_candidate(cand, patch, chain_evaluator=mock_evaluator)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.MUTATION_NO_EFFECT)

    # 17. Candidate whose failure is infrastructure-only
    def test_17_candidate_failure_is_infrastructure_only(self):
        cand, patch = make_valid_candidate(task_id="CAND-017", mutation_id="mut_017")
        def mock_evaluator(stage, p):
            if stage == "baseline":
                return 0, "PASS"
            if stage == "mutated":
                return 137, "INFRA_ERROR: OOMKilled container exit"
            return 0, "PASS"
        res = self.pool.register_candidate(cand, patch, chain_evaluator=mock_evaluator)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.INFRASTRUCTURE_FAILURE)

    # 18. Candidate whose reference repair does not restore PASS
    def test_18_candidate_reference_repair_does_not_restore_pass(self):
        cand, patch = make_valid_candidate(task_id="CAND-018", mutation_id="mut_018")
        def mock_evaluator(stage, p):
            if stage == "baseline":
                return 0, "PASS"
            if stage == "mutated":
                return 1, "FAIL: Mutation broke tests as expected"
            if stage == "repaired":
                return 1, "FAIL: Reference repair still fails tests"
            return 0, "PASS"
        res = self.pool.register_candidate(cand, patch, chain_evaluator=mock_evaluator)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.REFERENCE_REPAIR_FAILURE)

    # 19. Candidate whose reset hash differs
    def test_19_candidate_reset_hash_differs(self):
        cand, patch = make_valid_candidate(task_id="CAND-019", mutation_id="mut_019")
        def mock_evaluator(stage, p):
            if stage == "baseline":
                return 0, "PASS"
            if stage == "mutated":
                return 1, "FAIL"
            if stage == "repaired":
                return 0, "PASS"
            if stage == "reset_verify":
                return 1, "Reset hash does not match target file"
            return 0, "PASS"
        res = self.pool.register_candidate(cand, patch, chain_evaluator=mock_evaluator)
        self.assertFalse(res.admitted)
        self.assertEqual(res.rejection_reason, RejectionReason.RESET_FAILURE)

    # 20. Candidate generated with same seed twice
    def test_20_candidate_generated_with_same_seed_twice(self):
        cand1, patch1 = make_valid_candidate(
            task_id="CAND-020A", mutation_id="mut_020A", mutation_seed=77, patch="diff 1"
        )
        cand2, patch2 = make_valid_candidate(
            task_id="CAND-020B", mutation_id="mut_020B", mutation_seed=77, patch="diff 2"
        )
        res1 = self.pool.register_candidate(cand1, patch1)
        self.assertTrue(res1.admitted)
        res2 = self.pool.register_candidate(cand2, patch2)
        self.assertFalse(res2.admitted)
        self.assertEqual(res2.rejection_reason, RejectionReason.DUPLICATE_CONFIG)


if __name__ == "__main__":
    unittest.main()
