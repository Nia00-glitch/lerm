#!/usr/bin/env python3
"""Validates task definitions in holdout/tasks/ against _schema.yaml.

Usage:
    python3 scripts/validate_tasks.py
"""
from __future__ import annotations

import sys
from pathlib import Path
import yaml

VALID_CATEGORIES = {
    "recovery_after_failure",
    "long_horizon_state",
    "tool_misuse_trap",
    "unreliable_verifier",
}

VALID_FAILURE_KINDS = {
    "tool_returns_wrong",
    "file_deleted",
    "dep_broken",
    "network_flake",
    "",
    None,
}


def validate_task(path: Path) -> list[str]:
    errors = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(data, dict):
        return ["Root must be a mapping"]

    task_id = data.get("id")
    if not task_id or not str(task_id).startswith("HOLDOUT-"):
        errors.append("Missing or invalid 'id' (must match HOLDOUT-XXX)")

    cat = data.get("category")
    if cat not in VALID_CATEGORIES:
        errors.append(f"Invalid category '{cat}', expected one of {sorted(VALID_CATEGORIES)}")

    if data.get("public") is not False:
        errors.append("'public' must be explicitly False to protect holdout integrity")

    if not isinstance(data.get("horizon_steps"), int) or data["horizon_steps"] <= 0:
        errors.append("'horizon_steps' must be a positive integer")

    setup = data.get("setup", {})
    if not isinstance(setup, dict):
        errors.append("'setup' must be a dictionary")
    else:
        if not setup.get("image"):
            errors.append("setup.image must specify a container image digest or tag")

    instruction = data.get("instruction")
    if not instruction or not str(instruction).strip():
        errors.append("'instruction' must be a non-empty string")

    gt = data.get("ground_truth_checker", {})
    if not isinstance(gt, dict):
        errors.append("'ground_truth_checker' must be a dictionary")
    else:
        if not gt.get("entrypoint"):
            errors.append("ground_truth_checker.entrypoint must be specified")
        if gt.get("reads_agent_claim") is not False:
            errors.append("ground_truth_checker.reads_agent_claim must be False")

    if data.get("scoring") != "binary":
        errors.append("scoring must be 'binary'")

    valid_roles = {"historical", "calibration", "primary", "diagnostic"}
    role = data.get("data_role")
    if role not in valid_roles:
        errors.append(f"Invalid or missing 'data_role' '{role}', expected one of {sorted(valid_roles)}")

    hist_exp = data.get("historical_exposure")
    if not isinstance(hist_exp, bool):
        errors.append("'historical_exposure' must be explicitly boolean (True/False)")

    p_elig = data.get("primary_exp_loop_003_eligible")
    if not isinstance(p_elig, bool):
        errors.append("'primary_exp_loop_003_eligible' must be explicitly boolean (True/False)")

    if hist_exp is True and p_elig is not False:
        errors.append("FIREWALL VIOLATION: historical_exposure is True but primary_exp_loop_003_eligible is not False")

    return errors


def main() -> int:
    tasks_dir = Path("holdout/tasks")
    task_files = sorted(tasks_dir.glob("*.yaml"))
    task_files = [p for p in task_files if not p.name.startswith("_")]

    if not task_files:
        print(f"No task files found in {tasks_dir} (excluding _schema.yaml).")
        return 0

    print(f"Validating {len(task_files)} task(s) in {tasks_dir}...\n")
    failed = 0
    for path in task_files:
        errs = validate_task(path)
        if errs:
            failed += 1
            print(f"FAIL  {path.name}")
            for err in errs:
                print(f"      - {err}")
        else:
            print(f"PASS  {path.name}")

    print(f"\n{len(task_files) - failed}/{len(task_files)} task definitions valid.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
