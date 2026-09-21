"""Immutable Candidate Task Unit Schema for LERM EXP-LOOP-003 (Phase C).

Defines the exact schema, types, allowed ranges, and validation rules
for every fresh candidate task before entering validation or calibration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Mapping

SCHEMA_VERSION = "1.0.0"

VALID_DATA_ROLES = {
    "raw_candidate",
    "calibration",
    "primary",
    "diagnostic",
    "historical",
}

# Permitted mutation operators from procedural bug generator
ALLOWED_MUTATION_RULES = {
    "func_pm_ctrl_invert_if",
    "func_pm_ctrl_shuffle",
    "func_pm_remove_assign",
    "func_pm_remove_cond",
    "func_pm_remove_loop",
}

PROHIBITED_MUTATION_RULES = {
    "formatting_only",
    "comment_only",
    "dead_code",
    "test_file_edit",
    "dependency_change",
    "network_dependent",
}


class CandidateValidationError(ValueError):
    """Raised when a candidate task definition violates the frozen schema."""


@dataclass(frozen=True)
class CandidateTaskUnit:
    task_id: str
    source_repository: str
    source_commit: str
    mutation_id: str
    mutation_seed: int
    mutation_rule: str
    original_file_paths: tuple[str, ...]
    mutated_file_paths: tuple[str, ...]
    baseline_state_id: str
    mutated_state_id: str
    candidate_content_hash: str
    baseline_content_hash: str
    generation_timestamp: str
    generator_version: str
    generator_config_hash: str
    task_schema_version: str = SCHEMA_VERSION
    data_role: str = "raw_candidate"
    historical_exposure: bool = False
    primary_exp_loop_003_eligible: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Enforces all frozen validation rules fail-closed."""
        # 1. task_id: non-empty string, must match CAND-XXX or SWE-SM-XXX
        if not self.task_id or not isinstance(self.task_id, str):
            raise CandidateValidationError("task_id must be a non-empty string")
        if not re.match(r"^(CAND|SWE-SM)-[A-Za-z0-9_\-]+$", self.task_id):
            raise CandidateValidationError(
                f"task_id '{self.task_id}' invalid format (expected CAND-XXX or SWE-SM-XXX)"
            )

        # 2. source_repository: non-empty string
        if not self.source_repository or not isinstance(self.source_repository, str):
            raise CandidateValidationError("source_repository must be a non-empty string")

        # 3. source_commit: valid git sha format (7 to 40 hex chars)
        if not re.match(r"^[0-9a-f]{7,40}$", self.source_commit.lower()):
            raise CandidateValidationError(
                f"source_commit '{self.source_commit}' must be a 7-40 hex git commit hash"
            )

        # 4. mutation_id: non-empty string
        if not self.mutation_id or not isinstance(self.mutation_id, str):
            raise CandidateValidationError("mutation_id must be a non-empty string")

        # 5. mutation_seed: non-negative integer
        if not isinstance(self.mutation_seed, int) or self.mutation_seed < 0:
            raise CandidateValidationError(
                f"mutation_seed must be a non-negative integer, got {self.mutation_seed}"
            )

        # 6. mutation_rule: must be in ALLOWED_MUTATION_RULES
        if self.mutation_rule not in ALLOWED_MUTATION_RULES:
            raise CandidateValidationError(
                f"mutation_rule '{self.mutation_rule}' is not an allowed operator. Allowed: {sorted(ALLOWED_MUTATION_RULES)}"
            )

        # 7. File paths: non-empty tuples, valid repo paths
        if not self.original_file_paths or not all(isinstance(p, str) for p in self.original_file_paths):
            raise CandidateValidationError("original_file_paths must be a non-empty tuple of paths")
        if not self.mutated_file_paths or not all(isinstance(p, str) for p in self.mutated_file_paths):
            raise CandidateValidationError("mutated_file_paths must be a non-empty tuple of paths")
        for p in self.original_file_paths + self.mutated_file_paths:
            if "\\" in p:
                raise CandidateValidationError(
                    f"path '{p}' contains Windows backslashes; must be normalized to forward slashes '/'"
                )

        # 8. Hashes: 64-character hex strings (SHA-256)
        for name, h in [
            ("baseline_state_id", self.baseline_state_id),
            ("mutated_state_id", self.mutated_state_id),
            ("candidate_content_hash", self.candidate_content_hash),
            ("baseline_content_hash", self.baseline_content_hash),
            ("generator_config_hash", self.generator_config_hash),
        ]:
            if not re.match(r"^[0-9a-f]{64}$", h.lower()):
                raise CandidateValidationError(
                    f"{name} '{h}' must be a valid 64-character SHA-256 hex digest"
                )

        # 9. Schema version
        if self.task_schema_version != SCHEMA_VERSION:
            raise CandidateValidationError(
                f"task_schema_version '{self.task_schema_version}' mismatch (expected {SCHEMA_VERSION})"
            )

        # 10. data_role
        if self.data_role not in VALID_DATA_ROLES:
            raise CandidateValidationError(
                f"data_role '{self.data_role}' invalid (expected one of {sorted(VALID_DATA_ROLES)})"
            )

        # 11. historical_exposure: must strictly be False for fresh candidates
        if not isinstance(self.historical_exposure, bool) or self.historical_exposure is not False:
            raise CandidateValidationError("historical_exposure must strictly be boolean False")

        # 12. primary_eligibility: must be strictly boolean
        if not isinstance(self.primary_exp_loop_003_eligible, bool):
            raise CandidateValidationError("primary_exp_loop_003_eligible must be boolean")

        # 13. provenance: non-empty mapping
        if not isinstance(self.provenance, Mapping) or not self.provenance:
            raise CandidateValidationError("provenance must be a non-empty dictionary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
