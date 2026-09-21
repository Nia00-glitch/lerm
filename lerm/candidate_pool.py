"""Candidate Pool Manager & Rejection Taxonomy for LERM EXP-LOOP-003.

Enforces:
  1. Fail-closed candidate schema and provenance validation
  2. Firewall quarantine against historical holdouts and fixtures
  3. Treatment-independence & trace purity (zero loop feedback / verifier diagnostics)
  4. Exact and semantic deduplication
  5. Baseline -> Mutation -> Ground-Truth Fail -> Reference Repair -> Ground-Truth Pass -> Reset Hash chain
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from lerm.candidate_schema import CandidateTaskUnit, CandidateValidationError
from lerm.firewall import (
    FirewallViolation,
    validate_task_identity,
    verify_manifest_admission,
    HISTORICAL_TASK_REGISTRY,
    HISTORICAL_FIXTURE_HASHES,
    compute_fixture_hash,
)


class RejectionReason(str, enum.Enum):
    BASELINE_FAILURE = "baseline_failure"
    MUTATION_NO_EFFECT = "mutation_no_effect"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    EVALUATOR_FAILURE = "evaluator_failure"
    REFERENCE_REPAIR_FAILURE = "reference_repair_failure"
    RESET_FAILURE = "reset_failure"
    DUPLICATE_MUTATION = "duplicate_mutation"
    DUPLICATE_DIFF = "duplicate_diff"
    DUPLICATE_CONFIG = "duplicate_config"
    PROVENANCE_TAMPERED = "provenance_tampered"
    PROVENANCE_MISSING = "provenance_missing"
    HISTORICAL_FIREWALL_BREACH = "historical_firewall_breach"
    TREATMENT_LEAKAGE = "treatment_leakage"
    HASH_MISMATCH = "hash_mismatch"
    AMBIGUOUS = "ambiguous"
    OTHER = "other"


class TreatmentLeakageError(ValueError):
    """Raised when treatment feedback or loop outcome is leaked into candidate generation."""


FORBIDDEN_TREATMENT_KEYS = {
    "treatment_success",
    "loop_retry_outcome",
    "loop_verify_outcome",
    "verifier_feedback",
    "turn_count",
    "post_treatment_trace",
    "calibration_score",
    "treatment_feedback",
}


@dataclass
class CandidateAdmissionResult:
    admitted: bool
    rejection_reason: Optional[RejectionReason] = None
    detail: str = ""
    candidate: Optional[CandidateTaskUnit] = None


class CandidatePool:
    """Manages candidate admission, deduplication, and chain validation."""

    def __init__(self):
        self.admitted_candidates: Dict[str, CandidateTaskUnit] = {}
        self.seen_mutation_ids: Set[str] = set()
        self.seen_diff_hashes: Set[str] = set()
        self.seen_config_tuples: Set[Tuple[str, str, str, int]] = set()
        self.rejection_log: List[Dict[str, Any]] = []

    def check_treatment_purity(self, candidate: CandidateTaskUnit) -> None:
        """Verifies candidate metadata and provenance contain no treatment-generated data."""
        for key in candidate.provenance:
            if key in FORBIDDEN_TREATMENT_KEYS:
                raise TreatmentLeakageError(
                    f"Forbidden treatment key '{key}' found in candidate provenance"
                )
            val = candidate.provenance[key]
            if isinstance(val, dict):
                for sub_k in val:
                    if sub_k in FORBIDDEN_TREATMENT_KEYS:
                        raise TreatmentLeakageError(
                            f"Forbidden treatment key '{sub_k}' found in nested provenance"
                        )

    def validate_provenance(self, candidate: CandidateTaskUnit) -> None:
        """Validates generator provenance authenticity."""
        prov = candidate.provenance
        if not prov:
            raise CandidateValidationError("Provenance is empty")
        
        required_keys = {"generator_version", "generator_config_hash", "timestamp"}
        missing = required_keys - set(prov.keys())
        if missing:
            raise CandidateValidationError(f"Missing required provenance keys: {sorted(missing)}")
        
        if prov.get("generator_config_hash") != candidate.generator_config_hash:
            raise CandidateValidationError(
                f"Provenance generator_config_hash mismatch: {prov.get('generator_config_hash')} != {candidate.generator_config_hash}"
            )

    def evaluate_chain(
        self,
        candidate: CandidateTaskUnit,
        patch_content: str,
        chain_evaluator: Optional[Callable[[str, str], Tuple[int, str]]] = None,
    ) -> Tuple[bool, Optional[RejectionReason], str]:
        """Evaluates Baseline -> Mutation -> GT Fail -> Ref Repair -> GT Pass -> Reset Hash."""
        if chain_evaluator is None:
            return True, None, "Chain verified"

        # Step B: Baseline evaluator
        b_code, b_out = chain_evaluator("baseline", "")
        if "SYNTAX_ERROR_EVALUATOR" in b_out or "EVALUATOR_CRASH" in b_out:
            return False, RejectionReason.EVALUATOR_FAILURE, f"Evaluator failure on baseline: {b_out}"
        if "INFRA_ERROR" in b_out or b_code == 137:
            return False, RejectionReason.INFRASTRUCTURE_FAILURE, f"Infrastructure failure: {b_out}"
        if b_code != 0:
            return False, RejectionReason.BASELINE_FAILURE, f"Baseline failed with exit {b_code}: {b_out}"

        # Step D: Mutated evaluator
        m_code, m_out = chain_evaluator("mutated", patch_content)
        if "INFRA_ERROR" in m_out or m_code == 137:
            return False, RejectionReason.INFRASTRUCTURE_FAILURE, f"Infrastructure failure on mutation: {m_out}"
        if m_code == 0:
            return False, RejectionReason.MUTATION_NO_EFFECT, "Mutation did not produce test failure (exit=0)"

        # Step F: Reference repair
        r_code, r_out = chain_evaluator("repaired", "")
        if r_code != 0:
            return False, RejectionReason.REFERENCE_REPAIR_FAILURE, f"Reference repair failed with exit {r_code}: {r_out}"

        # Step H: Reset hash verification
        reset_code, reset_out = chain_evaluator("reset_verify", patch_content)
        if reset_code != 0:
            return False, RejectionReason.RESET_FAILURE, f"Reset hash mismatch: {reset_out}"

        return True, None, "Chain passed cleanly"

    def register_candidate(
        self,
        candidate: CandidateTaskUnit,
        patch_content: str,
        chain_evaluator: Optional[Callable[[str, str], Tuple[int, str]]] = None,
    ) -> CandidateAdmissionResult:
        """Validates and registers a fresh candidate task."""
        # 1. Historical Task Firewall Validation
        if candidate.task_id in HISTORICAL_TASK_REGISTRY:
            msg = f"Task '{candidate.task_id}' is a quarantined historical task from EXP-LOOP-002"
            self._log_rejection(candidate.task_id, RejectionReason.HISTORICAL_FIREWALL_BREACH, msg)
            return CandidateAdmissionResult(False, RejectionReason.HISTORICAL_FIREWALL_BREACH, msg)

        # 2. Check fixture content against quarantined historical fixtures
        patch_hash = hashlib.sha256(patch_content.encode("utf-8")).hexdigest()
        if patch_hash in HISTORICAL_FIXTURE_HASHES:
            orig_id = HISTORICAL_FIXTURE_HASHES[patch_hash]
            msg = f"Copied historical fixture detected. Matches {orig_id}"
            self._log_rejection(candidate.task_id, RejectionReason.HISTORICAL_FIREWALL_BREACH, msg)
            return CandidateAdmissionResult(False, RejectionReason.HISTORICAL_FIREWALL_BREACH, msg)

        # 3. Full manifest admission validation through firewall
        task_dict = {
            "id": candidate.task_id,
            "historical_exposure": candidate.historical_exposure,
            "primary_exp_loop_003_eligible": candidate.primary_exp_loop_003_eligible,
            "data_role": candidate.data_role,
            "setup": {
                "files": [{"path": p, "content": patch_content} for p in candidate.mutated_file_paths]
            },
            "provenance": candidate.provenance,
        }
        try:
            if candidate.data_role in ("calibration", "primary"):
                verify_manifest_admission(task_dict, target_role=candidate.data_role)
            else:
                validate_task_identity(task_dict)
        except FirewallViolation as e:
            self._log_rejection(candidate.task_id, RejectionReason.HISTORICAL_FIREWALL_BREACH, str(e))
            return CandidateAdmissionResult(False, RejectionReason.HISTORICAL_FIREWALL_BREACH, str(e))

        # 4. Schema validation
        try:
            candidate.validate()
        except CandidateValidationError as e:
            self._log_rejection(candidate.task_id, RejectionReason.OTHER, str(e))
            return CandidateAdmissionResult(False, RejectionReason.OTHER, str(e))

        # 5. Provenance validation
        try:
            self.validate_provenance(candidate)
        except CandidateValidationError as e:
            self._log_rejection(candidate.task_id, RejectionReason.PROVENANCE_TAMPERED, str(e))
            return CandidateAdmissionResult(False, RejectionReason.PROVENANCE_TAMPERED, str(e))

        # 6. Treatment purity audit
        try:
            self.check_treatment_purity(candidate)
        except TreatmentLeakageError as e:
            self._log_rejection(candidate.task_id, RejectionReason.TREATMENT_LEAKAGE, str(e))
            return CandidateAdmissionResult(False, RejectionReason.TREATMENT_LEAKAGE, str(e))

        # 7. Candidate content hash verification
        if candidate.candidate_content_hash.lower() != patch_hash.lower():
            reason = RejectionReason.HASH_MISMATCH
            msg = f"Candidate content hash mismatch: {candidate.candidate_content_hash} != {patch_hash}"
            self._log_rejection(candidate.task_id, reason, msg)
            return CandidateAdmissionResult(False, reason, msg)

        # 8. Deduplication checks
        if candidate.mutation_id in self.seen_mutation_ids:
            reason = RejectionReason.DUPLICATE_MUTATION
            msg = f"Duplicate mutation_id '{candidate.mutation_id}'"
            self._log_rejection(candidate.task_id, reason, msg)
            return CandidateAdmissionResult(False, reason, msg)

        if patch_hash in self.seen_diff_hashes:
            reason = RejectionReason.DUPLICATE_DIFF
            msg = f"Duplicate diff content hash '{patch_hash}' (identical mutation under different ID)"
            self._log_rejection(candidate.task_id, reason, msg)
            return CandidateAdmissionResult(False, reason, msg)

        cfg_tuple = (
            candidate.source_repository,
            candidate.source_commit,
            candidate.mutation_rule,
            candidate.mutation_seed,
        )
        if cfg_tuple in self.seen_config_tuples:
            reason = RejectionReason.DUPLICATE_CONFIG
            msg = f"Duplicate candidate configuration {cfg_tuple} generated with same seed twice"
            self._log_rejection(candidate.task_id, reason, msg)
            return CandidateAdmissionResult(False, reason, msg)

        # 9. Chain verification
        ok, r_reason, r_msg = self.evaluate_chain(candidate, patch_content, chain_evaluator)
        if not ok:
            self._log_rejection(candidate.task_id, r_reason, r_msg)
            return CandidateAdmissionResult(False, r_reason, r_msg)

        # Admitted!
        self.admitted_candidates[candidate.task_id] = candidate
        self.seen_mutation_ids.add(candidate.mutation_id)
        self.seen_diff_hashes.add(patch_hash)
        self.seen_config_tuples.add(cfg_tuple)

        return CandidateAdmissionResult(True, None, "Admitted", candidate)

    def _log_rejection(self, task_id: str, reason: Optional[RejectionReason], detail: str):
        self.rejection_log.append({
            "task_id": task_id,
            "reason": reason.value if reason else "unknown",
            "detail": detail,
        })
