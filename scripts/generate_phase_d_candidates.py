#!/usr/bin/env python3
"""Phase D1 Candidate Generation and Registration for LERM EXP-LOOP-003.

Generates K=30 candidate tasks from mewwts__addict.75284f95 using SWE-smith
procedural bug generation, verified through the fail-closed 9-step registration
pipeline and chain evaluator in lerm.candidate_pool.

Guarantees:
  1. Golden-copy preservation wrapper (mewwts__addict.75284f95.golden)
  2. Master Seed Hierarchy (Protocol 05)
  3. Fail-closed candidate schema (Protocol 01)
  4. 6-stage chain evaluation (Baseline -> Mutation -> Ground-Truth Fail ->
     Reference Repair -> Ground-Truth Pass -> Reset Verification)
  5. Cryptographic manifest freezing (Protocol 10)
"""
from __future__ import annotations

import datetime
import glob
import hashlib
import json
import os
import random
import shutil
import stat
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Tuple

# Windows resource shim for SWE-smith
sys.modules['resource'] = types.ModuleType('resource')
sys.path.insert(0, os.path.abspath('swe-smith'))
sys.path.insert(0, os.path.abspath('.'))

import swesmith.constants
from swesmith.bug_gen.procedural import MAP_EXT_TO_MODIFIERS
from swesmith.bug_gen.procedural.generate import main as swesmith_main

from lerm.candidate_schema import (
    ALLOWED_MUTATION_RULES,
    CandidateTaskUnit,
    CandidateValidationError,
)
from lerm.candidate_pool import CandidatePool, CandidateAdmissionResult, RejectionReason

# --- Mechanical Gate for Phase D Authorization (Protocol v2 §19, §27, §29) ---
def verify_phase_d_authorization(
    decisions_path: str = "docs/DECISIONS.md",
    reports_dir: str = "reports/phase-d",
) -> None:
    """Verifies that Phase D candidate generation is formally authorized.
    
    Refuses to run if any Phase D audit records a BLOCKED status without
    a corresponding superseding entry in docs/DECISIONS.md (e.g. DECISION-0002).
    """
    # 1. Scan audit reports for BLOCKED verdicts
    blocked_reports = []
    if os.path.exists(reports_dir):
        for audit_file in sorted(glob.glob(os.path.join(reports_dir, "*AUDIT*.md"))):
            with open(audit_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "FINAL AUDIT STATUS: BLOCKED" in content or "PHASE D BLOCKED" in content or "Gate Status: BLOCKED" in content:
                blocked_reports.append(os.path.basename(audit_file))
                
    if not blocked_reports:
        return

    # 2. Check for superseding decision in docs/DECISIONS.md
    has_superseding_decision = False
    superseding_decision_id = None
    if os.path.exists(decisions_path):
        with open(decisions_path, "r", encoding="utf-8") as f:
            decisions_text = f.read()
        # Look for DECISION-0002 or explicit resolution authorizing candidate pool
        if "DECISION-0002" in decisions_text and ("single-repo" in decisions_text.lower() or "addict-only" in decisions_text.lower() or "phase d-partial" in decisions_text.lower()):
            has_superseding_decision = True
            superseding_decision_id = "DECISION-0002"

    if not has_superseding_decision:
        raise RuntimeError(
            f"[MECHANICAL GATE HALT] Phase D candidate generation is BLOCKED by {blocked_reports}. "
            f"No superseding decision authorizing candidate pool execution found in {decisions_path}. "
            f"Execution halted under LERM Protocol v2 (§0, §19, §27, §29)."
        )
    print(f"[MECHANICAL GATE PASS] Phase D authorized via {superseding_decision_id} in {decisions_path}.")

# Execute mechanical gate check
verify_phase_d_authorization()


# --- Golden-Copy Wrapper Support ---
_orig_rmtree = shutil.rmtree
def _win_rmtree(path: str, *args, **kwargs):
    def on_err(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass
    return _orig_rmtree(path, onerror=on_err)

shutil.rmtree = _win_rmtree


def reseed_all(s: int) -> None:
    random.seed(s)
    for ext, pms in MAP_EXT_TO_MODIFIERS.items():
        for pm in pms:
            if hasattr(pm, 'rand'):
                pm.rand.seed(s)


def ensure_repo_restored(golden_dir: str, target_dir: str, pinned_head: str) -> None:
    if os.path.exists(target_dir):
        _win_rmtree(target_dir)
    shutil.copytree(golden_dir, target_dir)
    
    # Verify commit
    res = subprocess.run(
        ["git", "-C", target_dir, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    commit = res.stdout.strip()
    if commit != pinned_head:
        raise RuntimeError(f"Restored repo HEAD {commit} does not match pinned HEAD {pinned_head}")
    
    # Verify clean status
    stat_res = subprocess.run(
        ["git", "-C", target_dir, "status", "--short"],
        capture_output=True,
        text=True,
        check=True,
    )
    if stat_res.stdout.strip():
        raise RuntimeError(f"Restored repo is not clean: {stat_res.stdout}")


def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def make_chain_evaluator(repo_dir: str):
    """Creates a 6-stage chain evaluator for mewwts__addict.75284f95."""
    
    def evaluate(stage: str, patch_content: str) -> Tuple[int, str]:
        python_exe = sys.executable
        
        if stage == "baseline":
            p = subprocess.run(
                [python_exe, "-m", "pytest", "test_addict.py", "-q"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return p.returncode, p.stdout + p.stderr

        elif stage == "mutated":
            # Apply patch
            p_apply = subprocess.run(
                ["git", "apply", "--whitespace=nowarn"],
                input=patch_content,
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if p_apply.returncode != 0:
                return 1, f"INFRA_ERROR: git apply failed: {p_apply.stderr}"
            
            p_test = subprocess.run(
                [python_exe, "-m", "pytest", "test_addict.py", "-q"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return p_test.returncode, p_test.stdout + p_test.stderr

        elif stage == "repaired":
            # Revert patch
            p_revert = subprocess.run(
                ["git", "checkout", "--", "."],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if p_revert.returncode != 0:
                return 1, f"INFRA_ERROR: git checkout failed: {p_revert.stderr}"
            
            p_test = subprocess.run(
                [python_exe, "-m", "pytest", "test_addict.py", "-q"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return p_test.returncode, p_test.stdout + p_test.stderr

        elif stage == "reset_verify":
            p_stat = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=15,
            )
            clean = len(p_stat.stdout.strip()) == 0
            return (0, "clean") if clean else (1, f"dirty: {p_stat.stdout}")

        return 1, f"Unknown stage: {stage}"

    return evaluate


def generate_candidate_pool(target_k: int = 30) -> tuple[CandidatePool, dict[str, str]]:
    repo_name = "mewwts__addict.75284f95"
    golden_dir = os.path.abspath(f"{repo_name}.golden")
    working_dir = os.path.abspath(repo_name)
    pinned_head = "75284f9593dfb929cadd900aff9e35e7c7aec54b"
    generator_commit = "9b74ac08118a85c39c356802f7961893af73e07f"
    generator_config_hash = "8f03dc16a4e320f3e691ba73efcb0cf7925e04e963ecf6d9a9cf58a5c37eb61b"
    master_seed = 20260921

    if not os.path.exists(golden_dir):
        raise FileNotFoundError(f"Golden copy '{golden_dir}' not found.")

    ensure_repo_restored(golden_dir, working_dir, pinned_head)
    
    baseline_file_path = os.path.join(working_dir, "addict", "addict.py")
    baseline_content_hash = compute_file_sha256(baseline_file_path)
    
    pool = CandidatePool()
    chain_evaluator = make_chain_evaluator(working_dir)
    admitted_patches: dict[str, str] = {}
    
    batch_num = 1
    candidate_counter = 1
    
    print(f"=== Starting Candidate Generation: Target K = {target_k} ===")
    print(f"Repository: {repo_name} @ {pinned_head[:8]}")
    print(f"Baseline Content Hash (addict/addict.py): {baseline_content_hash}")
    
    while len(pool.admitted_candidates) < target_k:
        seed = (master_seed + 200 + batch_num) % 100000
        print(f"\n--- Batch {batch_num} (Seed = {seed}) | Admitted: {len(pool.admitted_candidates)}/{target_k} ---")
        
        # 1. Prepare working copy from golden
        ensure_repo_restored(golden_dir, working_dir, pinned_head)
        
        # 2. Clean SWE-smith bug gen log dir
        out_dir = os.path.join(swesmith.constants.LOG_DIR_BUG_GEN, repo_name)
        if os.path.exists(out_dir):
            _win_rmtree(out_dir)
            
        # 3. Reseed and invoke SWE-smith main()
        reseed_all(seed)
        swesmith_main(repo_name, max_bugs=1, seed=seed, max_entities=10)
        
        # 4. Immediately restore working copy from golden (since SWE-smith deleted it)
        ensure_repo_restored(golden_dir, working_dir, pinned_head)
        
        # 5. Discover all generated bug metadata and diffs
        meta_files = sorted(glob.glob(os.path.join(out_dir, "**", "metadata__*.json"), recursive=True))
        print(f"Batch {batch_num} generated {len(meta_files)} raw bug artifacts.")
        
        for meta_file in meta_files:
            if len(pool.admitted_candidates) >= target_k:
                break
                
            diff_file = meta_file.replace("metadata__", "bug__").replace(".json", ".diff")
            if not os.path.exists(diff_file):
                continue
                
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            with open(diff_file, "r", encoding="utf-8") as f:
                raw_patch = f.read()
                
            # Normalize path separators to forward slash (Protocol 01 Rule 6 & Git compatibility)
            norm_patch = raw_patch.replace(chr(92), "/")
            patch_hash = hashlib.sha256(norm_patch.encode("utf-8")).hexdigest()
            
            rule_name = meta.get("strategy") or meta.get("rule") or ""
            # Check allowed mutation rule
            if rule_name not in ALLOWED_MUTATION_RULES:
                continue
                
            mut_id = os.path.basename(meta_file).replace("metadata__", "").replace(".json", "")
            task_id = f"CAND-{candidate_counter:03d}"
            gen_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            # Compute mutated state id by temporarily applying patch
            p_apply = subprocess.run(
                ["git", "apply", "--whitespace=nowarn"],
                input=norm_patch,
                cwd=working_dir,
                capture_output=True,
                text=True,
            )
            if p_apply.returncode == 0:
                mutated_file_hash = compute_file_sha256(baseline_file_path)
                subprocess.run(["git", "checkout", "--", "."], cwd=working_dir, capture_output=True)
            else:
                mutated_file_hash = hashlib.sha256((baseline_content_hash + patch_hash).encode()).hexdigest()
                
            cand = CandidateTaskUnit(
                task_id=task_id,
                source_repository=repo_name,
                source_commit=pinned_head,
                mutation_id=mut_id,
                mutation_seed=seed,
                mutation_rule=rule_name,
                original_file_paths=("addict/addict.py",),
                mutated_file_paths=("addict/addict.py",),
                baseline_state_id=baseline_content_hash,
                mutated_state_id=mutated_file_hash,
                candidate_content_hash=patch_hash,
                baseline_content_hash=baseline_content_hash,
                generation_timestamp=gen_timestamp,
                generator_version=f"swe-smith-{generator_commit[:7]}",
                generator_config_hash=generator_config_hash,
                task_schema_version="1.0.0",
                data_role="raw_candidate",
                historical_exposure=False,
                primary_exp_loop_003_eligible=True,
                provenance={
                    "generator_version": f"swe-smith-{generator_commit[:7]}",
                    "generator_config_hash": generator_config_hash,
                    "timestamp": gen_timestamp,
                    "batch": batch_num,
                    "seed": seed,
                },
            )
            
            # Register candidate through 9-step pipeline
            res: CandidateAdmissionResult = pool.register_candidate(cand, norm_patch, chain_evaluator)
            if res.admitted:
                admitted_patches[task_id] = norm_patch
                print(f"  [+] ADMITTED: {task_id} | Rule: {rule_name} | Seed: {seed} | Patch SHA: {patch_hash[:12]}")
                candidate_counter += 1
            else:
                print(f"  [-] REJECTED: {task_id} | Reason: {res.rejection_reason.value} | Detail: {res.detail[:80]}")
                
        batch_num += 1
        if batch_num > 100:
            raise RuntimeError(f"Exceeded 100 batches without reaching target K={target_k} (currently {len(pool.admitted_candidates)})")

    print(f"\n=== Candidate Pool Generation Complete ===")
    print(f"Total Admitted: {len(pool.admitted_candidates)}/{target_k}")
    print(f"Total Rejections Logged: {len(pool.rejection_log)}")
    return pool, admitted_patches


def save_manifest_and_artifacts(pool: CandidatePool, patches: dict[str, str], out_dir: str = "data/phase-d") -> str:
    os.makedirs(out_dir, exist_ok=True)
    patches_dir = os.path.join(out_dir, "patches")
    os.makedirs(patches_dir, exist_ok=True)
    
    # 1. Save patches
    for task_id, patch in patches.items():
        with open(os.path.join(patches_dir, f"{task_id}.diff"), "w", encoding="utf-8") as f:
            f.write(patch)
            
    # 2. Save candidates.jsonl
    jsonl_path = os.path.join(out_dir, "candidates.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for cand in pool.admitted_candidates.values():
            cand_dict = {
                "task_id": cand.task_id,
                "source_repository": cand.source_repository,
                "source_commit": cand.source_commit,
                "mutation_id": cand.mutation_id,
                "mutation_seed": cand.mutation_seed,
                "mutation_rule": cand.mutation_rule,
                "original_file_paths": list(cand.original_file_paths),
                "mutated_file_paths": list(cand.mutated_file_paths),
                "baseline_state_id": cand.baseline_state_id,
                "mutated_state_id": cand.mutated_state_id,
                "candidate_content_hash": cand.candidate_content_hash,
                "baseline_content_hash": cand.baseline_content_hash,
                "generation_timestamp": cand.generation_timestamp,
                "generator_version": cand.generator_version,
                "generator_config_hash": cand.generator_config_hash,
                "task_schema_version": cand.task_schema_version,
                "data_role": cand.data_role,
                "historical_exposure": cand.historical_exposure,
                "primary_exp_loop_003_eligible": cand.primary_exp_loop_003_eligible,
                "provenance": cand.provenance,
            }
            f.write(json.dumps(cand_dict) + "\n")
            
    # 3. Save candidates_manifest.yaml
    manifest_path = os.path.join(out_dir, "candidates_manifest.yaml")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    lines = [
        'schema_version: "1.0.0"',
        'manifest_id: "EXP-LOOP-003-CANDIDATES"',
        f'generated_at: "{now_iso}"',
        'master_seed: 20260921',
        'generator_commit: "9b74ac08118a85c39c356802f7961893af73e07f"',
        f'total_admitted: {len(pool.admitted_candidates)}',
        'tasks:',
    ]
    for cand in pool.admitted_candidates.values():
        lines.append(f'  - id: "{cand.task_id}"')
        lines.append(f'    source_repository: "{cand.source_repository}"')
        lines.append(f'    source_commit: "{cand.source_commit}"')
        lines.append(f'    mutation_id: "{cand.mutation_id}"')
        lines.append(f'    mutation_seed: {cand.mutation_seed}')
        lines.append(f'    mutation_rule: "{cand.mutation_rule}"')
        lines.append('    original_file_paths:')
        for p in cand.original_file_paths:
            lines.append(f'      - "{p}"')
        lines.append('    mutated_file_paths:')
        for p in cand.mutated_file_paths:
            lines.append(f'      - "{p}"')
        lines.append(f'    baseline_state_id: "{cand.baseline_state_id}"')
        lines.append(f'    mutated_state_id: "{cand.mutated_state_id}"')
        lines.append(f'    candidate_content_hash: "{cand.candidate_content_hash}"')
        lines.append(f'    baseline_content_hash: "{cand.baseline_content_hash}"')
        lines.append(f'    generation_timestamp: "{cand.generation_timestamp}"')
        lines.append(f'    generator_version: "{cand.generator_version}"')
        lines.append(f'    generator_config_hash: "{cand.generator_config_hash}"')
        lines.append(f'    task_schema_version: "{cand.task_schema_version}"')
        lines.append(f'    data_role: "{cand.data_role}"')
        lines.append(f'    historical_exposure: {str(cand.historical_exposure).lower()}')
        lines.append(f'    primary_exp_loop_003_eligible: {str(cand.primary_exp_loop_003_eligible).lower()}')
        lines.append('    provenance:')
        lines.append(f'      generator_version: "{cand.provenance.get("generator_version")}"')
        lines.append(f'      generator_config_hash: "{cand.provenance.get("generator_config_hash")}"')
        lines.append(f'      timestamp: "{cand.provenance.get("timestamp")}"')
        lines.append(f'      batch: {cand.provenance.get("batch")}')
        lines.append(f'      seed: {cand.provenance.get("seed")}')
        
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
        
    # 4. Save rejection log
    rejection_path = os.path.join(out_dir, "rejection_log.json")
    with open(rejection_path, "w", encoding="utf-8") as f:
        json.dump(pool.rejection_log, f, indent=2)
        
    # 5. Compute Manifest SHA-256
    manifest_hash = compute_file_sha256(manifest_path)
    hash_path = os.path.join(out_dir, "MANIFEST_SHA256.txt")
    with open(hash_path, "w", encoding="utf-8") as f:
        f.write(f"{manifest_hash}  candidates_manifest.yaml\n")
        
    print(f"\nSaved {len(pool.admitted_candidates)} candidates to {out_dir}")
    print(f"Manifest SHA-256: {manifest_hash}")
    return manifest_hash


if __name__ == "__main__":
    pool, patches = generate_candidate_pool(target_k=30)
    manifest_hash = save_manifest_and_artifacts(pool, patches)
