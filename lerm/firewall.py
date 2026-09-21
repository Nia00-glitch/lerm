"""Data firewall for LERM experiments (Remediated & Fail-Closed).

CRITICAL CAUSAL PRINCIPLE:
Historical tasks and data from EXP-LOOP-002 and earlier runs MUST NOT enter:
  - calibration datasets
  - primary causal experiment manifests
  - primary analysis traces

The firewall is fail-closed, validates strict schema types, enforces an
immutable historical registry, detects copied fixtures via SHA-256 hashes,
and validates task identity across both manifest admission and trace ingestion.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping


class FirewallViolation(RuntimeError):
    """Raised when data across firewalled roles is illegally mixed or admitted."""


# -----------------------------------------------------------------------------
# Authoritative Immutable Historical Registry (EXP-LOOP-002 Holdout Tasks)
# -----------------------------------------------------------------------------
HISTORICAL_TASK_REGISTRY: dict[str, dict[str, Any]] = {
    "HOLDOUT-001": {
        "experiment_id": "EXP-LOOP-002",
        "historical_exposure": True,
        "fixture_hash": "6d873be45658bad74390d98b315f170bd3b7ecac5782c31c487ef2c6e91f5f6a",
        "content_hash": "cf4370f85874fd3622ae1ccb36fbd6fc68e324f90d068622c97e840f4480c428",
    },
    "HOLDOUT-002": {
        "experiment_id": "EXP-LOOP-002",
        "historical_exposure": True,
        "fixture_hash": "c53b59f136f689957871e461449223d72a78cef7f5206ae325c74781eaab8c52",
        "content_hash": "30e3a5c5a91fb6beb33b8993cf7a6c13baa16b9bb355c3cdfe7d68e022b349c5",
    },
    "HOLDOUT-003": {
        "experiment_id": "EXP-LOOP-002",
        "historical_exposure": True,
        "fixture_hash": "d705227dfb66466bcfb1bccabc7e03b55a494c11c435c3d3a74d1c655b6c2146",
        "content_hash": "c83b3f5a18b411d7b6f48118c234016978d9475f6dc5d6c3ec65ea2e413cbc1c",
    },
    "HOLDOUT-004": {
        "experiment_id": "EXP-LOOP-002",
        "historical_exposure": True,
        "fixture_hash": "57157f4eea810d634201208683ad67ef1fc353b5101c71dd498c7a9085852fbf",
        "content_hash": "ef64355b6f5f78755612070e2475891c045e38849f7eafa3c3962545123eadbe",
    },
}

# Reverse lookup by fixture hash to catch copied / renamed tasks
HISTORICAL_FIXTURE_HASHES: dict[str, str] = {
    meta["fixture_hash"]: tid for tid, meta in HISTORICAL_TASK_REGISTRY.items()
}


@dataclass(frozen=True)
class TaskProvenance:
    task_id: str
    is_historical: bool
    is_eligible_primary: bool
    fixture_hash: str
    provenance_info: dict[str, Any]


def compute_fixture_hash(task_data: Mapping[str, Any]) -> str:
    """Computes a canonical SHA-256 hash of all fixture files in setup."""
    files = task_data.get("setup", {}).get("files", [])
    if not files:
        return ""
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: str(x.get("path", ""))):
        h.update(str(f.get("path", "")).encode())
        h.update(str(f.get("content", "")).encode())
    return h.hexdigest()


def validate_task_identity(task_data: Mapping[str, Any]) -> TaskProvenance:
    """Authoritatively resolves task identity, historical status, and provenance.

    Fails closed:
      - Rejects missing or invalid task ID
      - Rejects missing, string, or non-boolean exposure/eligibility flags
      - Rejects known historical tasks regardless of caller flags
      - Rejects tasks with matching historical fixture hashes
      - Rejects unverified tasks lacking provenance
    """
    if not isinstance(task_data, Mapping):
        raise FirewallViolation("REJECTED: Task data must be a valid mapping")

    # 1. Validate task ID
    task_id = task_data.get("id")
    if not task_id or not isinstance(task_id, str) or not task_id.strip():
        raise FirewallViolation("REJECTED: Missing or invalid task ID")
    task_id = task_id.strip()

    # 2. Strict Type Validation on boolean flags (Fail-Closed)
    if "historical_exposure" not in task_data:
        raise FirewallViolation(f"REJECTED: Task '{task_id}' missing 'historical_exposure' field")
    hist_exp = task_data["historical_exposure"]
    if not isinstance(hist_exp, bool):
        raise FirewallViolation(
            f"REJECTED: Task '{task_id}' has non-boolean historical_exposure='{hist_exp}' (type {type(hist_exp).__name__})"
        )

    if "primary_exp_loop_003_eligible" not in task_data:
        raise FirewallViolation(
            f"REJECTED: Task '{task_id}' missing 'primary_exp_loop_003_eligible' field"
        )
    p_elig = task_data["primary_exp_loop_003_eligible"]
    if not isinstance(p_elig, bool):
        raise FirewallViolation(
            f"REJECTED: Task '{task_id}' has non-boolean primary_exp_loop_003_eligible='{p_elig}' (type {type(p_elig).__name__})"
        )

    # 3. Check Authoritative Immutable Registry by ID
    is_known_historical_id = task_id in HISTORICAL_TASK_REGISTRY
    if is_known_historical_id:
        if hist_exp is False or p_elig is True:
            raise FirewallViolation(
                f"REJECTED: Metadata tampering detected on '{task_id}'. "
                "Task is registered as an immutable historical holdout; caller flags are invalid."
            )
        return TaskProvenance(
            task_id=task_id,
            is_historical=True,
            is_eligible_primary=False,
            fixture_hash=HISTORICAL_TASK_REGISTRY[task_id]["fixture_hash"],
            provenance_info={"experiment_id": "EXP-LOOP-002", "source": "registry"},
        )

    # 4. Check Fixture Hash against known historical fixtures (Anti-Copy Protection)
    fix_hash = compute_fixture_hash(task_data)
    if fix_hash and fix_hash in HISTORICAL_FIXTURE_HASHES:
        orig_id = HISTORICAL_FIXTURE_HASHES[fix_hash]
        raise FirewallViolation(
            f"REJECTED: Copied historical artifact detected. Task '{task_id}' has byte-identical "
            f"fixture hash ({fix_hash[:16]}...) to historical task '{orig_id}'."
        )

    # 5. Caller metadata consistency check
    if hist_exp is True or p_elig is False or task_data.get("data_role") == "historical":
        return TaskProvenance(
            task_id=task_id,
            is_historical=True,
            is_eligible_primary=False,
            fixture_hash=fix_hash,
            provenance_info=dict(task_data.get("provenance") or {}),
        )

    # 6. Fresh Candidate Provenance Requirement
    provenance = task_data.get("provenance")
    if not provenance or not isinstance(provenance, Mapping):
        raise FirewallViolation(
            f"REJECTED: Fresh candidate '{task_id}' missing required provenance metadata."
        )

    return TaskProvenance(
        task_id=task_id,
        is_historical=False,
        is_eligible_primary=True,
        fixture_hash=fix_hash,
        provenance_info=dict(provenance),
    )


def verify_manifest_admission(task_data: Mapping[str, Any], target_role: str = "primary") -> TaskProvenance:
    """Validates whether a candidate task may enter a manifest for target_role.

    All roles (primary, calibration, diagnostic) pass through historical firewall.
    """
    provenance = validate_task_identity(task_data)

    if provenance.is_historical:
        if target_role in ("primary", "calibration"):
            raise FirewallViolation(
                f"REJECTED: Task '{provenance.task_id}' has historical_exposure=True. "
                f"Historical tasks from EXP-LOOP-002 cannot enter EXP-LOOP-003 {target_role}."
            )
        elif target_role in ("diagnostic", "historical"):
            return provenance
        else:
            raise FirewallViolation(f"REJECTED: Unauthorized target_role '{target_role}'")

    if target_role == "primary":
        if not provenance.is_eligible_primary:
            raise FirewallViolation(
                f"REJECTED: Task '{provenance.task_id}' is marked primary_exp_loop_003_eligible=False. "
                "Admission refused."
            )

    return provenance


def verify_dataset_separation(records: list[Mapping[str, Any]], expected_role: str) -> None:
    """Verifies all records match expected_role AND blocks historical tasks from causal datasets."""
    for r in records:
        role = r.get("data_role", "unknown")
        if role != expected_role:
            raise FirewallViolation(
                f"REJECTED: Contamination detected. Record '{r.get('run_id')}' has data_role='{role}', "
                f"expected '{expected_role}'."
            )
        tid = r.get("task_id", "")
        if expected_role in ("primary", "calibration"):
            if tid in HISTORICAL_TASK_REGISTRY:
                raise FirewallViolation(
                    f"REJECTED: Historical task '{tid}' detected in '{expected_role}' trace dataset."
                )


def verify_manifest(manifest_entries: list[Any], target_role: str = "primary") -> list[TaskProvenance]:
    """Validates an entire manifest atomically. Rejects bare IDs or invalid tasks."""
    if not manifest_entries:
        raise FirewallViolation("REJECTED: Empty manifest")

    validated = []
    for entry in manifest_entries:
        if not isinstance(entry, Mapping):
            raise FirewallViolation(
                f"REJECTED: Manifest entry must be a mapping with full metadata, got '{entry}'"
            )
        prov = verify_manifest_admission(entry, target_role=target_role)
        validated.append(prov)
    return validated
