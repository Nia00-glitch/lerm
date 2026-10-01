#!/usr/bin/env python3
"""Phase D Compound Candidate Generator for EXP-LOOP-003 (Protocol 03 §4 & DECISION-0006).

Constructs compound (higher-order) candidates by systematically combining
qualifying single-function procedural mutations on mewwts__addict.75284f95.

Guarantees:
  1. Strict pair composition from approved single-function mutations.
  2. 6-stage chain evaluation in container (Baseline -> Compound Apply -> Ground-Truth Fail -> Reset).
  3. Non-overlapping hunk verification.
  4. Generation of unified diffs (data/phase-d/patches/COMP-*.diff).
  5. Cryptographic candidate manifest freezing (data/phase-d/compound_manifest.yaml).
"""
from __future__ import annotations

import datetime
import hashlib
import itertools
import json
import os
import subprocess
import sys
import yaml
from pathlib import Path

CONTAINER_NAME = "oh-agent-server-1QdXehKsSEZITvWvP0Tp1C"
WORKDIR = "/workspace/project"
PATCHES_DIR = Path("data/phase-d/patches")
MANIFEST_OUT = Path("data/phase-d/compound_manifest.yaml")
JSONL_OUT = Path("data/phase-d/compound_candidates.jsonl")

# The 7 approved base candidates
BASE_CANDIDATES = [
    {"id": "CAND-001", "func": "setdefault", "rule": "func_pm_remove_assign", "diff": "CAND-001.diff"},
    {"id": "CAND-003", "func": "__init__", "rule": "func_pm_ctrl_invert_if", "diff": "CAND-003.diff"},
    {"id": "CAND-006", "func": "_hook", "rule": "func_pm_remove_cond", "diff": "CAND-006.diff"},
    {"id": "CAND-008", "func": "freeze", "rule": "func_pm_remove_cond", "diff": "CAND-008.diff"},
    {"id": "CAND-009", "func": "to_dict", "rule": "func_pm_ctrl_shuffle", "diff": "CAND-009.diff"},
    {"id": "CAND-021", "func": "__setitem__", "rule": "func_pm_remove_assign", "diff": "CAND-021.diff"},
    {"id": "CAND-026", "func": "update", "rule": "func_pm_ctrl_invert_if", "diff": "CAND-026.diff"},
]


def unpause():
    subprocess.run(["docker", "unpause", CONTAINER_NAME], capture_output=True)


def reset_repo():
    unpause()
    subprocess.run(
        ["docker", "exec", "-u", "0", CONTAINER_NAME, "sh", "-c", f"git -C {WORKDIR} checkout -- addict/addict.py"],
        check=True
    )
    res = subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "python3", "-m", "pytest", f"{WORKDIR}/test_addict.py", "-q"],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        raise RuntimeError("Clean repository reset failed")


def main():
    print(f"Generating Compound Candidates under Protocol 03 §4 and DECISION-0006...")
    reset_repo()
    
    pairs = list(itertools.combinations(BASE_CANDIDATES, 2))
    print(f"Total potential candidate pairs: {len(pairs)}")
    
    generated_tasks = []
    jsonl_records = []
    
    for idx, (c1, c2) in enumerate(pairs, start=1):
        comp_id = f"COMP-{idx:03d}"
        d1_path = PATCHES_DIR / c1["diff"]
        d2_path = PATCHES_DIR / c2["diff"]
        
        with open(d1_path, "rb") as f:
            d1_bytes = f.read().replace(b"\r\n", b"\n")
        with open(d2_path, "rb") as f:
            d2_bytes = f.read().replace(b"\r\n", b"\n")
            
        reset_repo()
        
        # Apply d1
        p1 = subprocess.Popen(
            ["docker", "exec", "-u", "0", "-i", CONTAINER_NAME, "sh", "-c", f"git -C {WORKDIR} apply --whitespace=nowarn"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        _, err1 = p1.communicate(input=d1_bytes)
        
        # Apply d2
        p2 = subprocess.Popen(
            ["docker", "exec", "-u", "0", "-i", CONTAINER_NAME, "sh", "-c", f"git -C {WORKDIR} apply --whitespace=nowarn"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        _, err2 = p2.communicate(input=d2_bytes)
        
        if p1.returncode != 0 or p2.returncode != 0:
            print(f"[{comp_id}] Collision between {c1['id']} and {c2['id']}. Skipping.")
            reset_repo()
            continue
            
        # Verify tests fail
        res = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "python3", "-m", "pytest", f"{WORKDIR}/test_addict.py", "-q"],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            print(f"[{comp_id}] Tests unexpectedly passed. Skipping.")
            reset_repo()
            continue
            
        test_summary = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
        
        # Extract combined unified diff
        diff_res = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "git", "-C", WORKDIR, "diff", "addict/addict.py"],
            capture_output=True, text=True
        )
        unified_diff = diff_res.stdout
        diff_out_path = PATCHES_DIR / f"{comp_id}.diff"
        with open(diff_out_path, "w", encoding="utf-8") as df:
            df.write(unified_diff)
            
        diff_hash = hashlib.sha256(unified_diff.encode("utf-8")).hexdigest()
        
        task_record = {
            "id": comp_id,
            "constituent_tasks": [c1["id"], c2["id"]],
            "constituent_functions": [c1["func"], c2["func"]],
            "constituent_rules": [c1["rule"], c2["rule"]],
            "source_repository": "mewwts__addict.75284f95",
            "source_commit": "75284f9593dfb929cadd900aff9e35e7c7aec54b",
            "patch_path": f"data/phase-d/patches/{comp_id}.diff",
            "patch_hash": diff_hash,
            "failure_signature": test_summary,
            "data_role": "calibration",
            "generation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        
        generated_tasks.append(task_record)
        jsonl_records.append(task_record)
        print(f"[{comp_id}] Registered ({c1['id']}:{c1['func']} + {c2['id']}:{c2['func']}) -> {test_summary}")
        reset_repo()

    # Write manifest
    manifest_data = {
        "schema_version": "2.0.0",
        "manifest_id": "EXP-LOOP-003-COMPOUND-CANDIDATES",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_generated": len(generated_tasks),
        "tasks": generated_tasks,
    }
    
    with open(MANIFEST_OUT, "w", encoding="utf-8") as mf:
        yaml.dump(manifest_data, mf, sort_keys=False)
        
    with open(JSONL_OUT, "w", encoding="utf-8") as jf:
        for r in jsonl_records:
            jf.write(json.dumps(r) + "\n")
            
    # Compute manifest hash
    manifest_bytes = open(MANIFEST_OUT, "rb").read()
    m_hash = hashlib.sha256(manifest_bytes).hexdigest()
    with open("data/phase-d/COMPOUND_MANIFEST_SHA256.txt", "w", encoding="utf-8") as hf:
        hf.write(m_hash + "\n")
        
    print(f"\nSuccessfully generated and frozen {len(generated_tasks)} compound candidates.")
    print(f"Manifest: {MANIFEST_OUT} (SHA256: {m_hash})")


if __name__ == "__main__":
    main()
