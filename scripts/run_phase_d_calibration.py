#!/usr/bin/env python3
"""Phase D2/D3 Calibration Protocol Execution for LERM EXP-LOOP-003.

Evaluates K=30 candidate tasks under Protocol 06:
  - Condition: 'single_shot_calibration' (T=1, 0 feedback, 0 retries)
  - Gate A12: trace_purity.py audit on every trial
  - Stage 1: Preliminary Screen (N1 = 10)
    * X1 <= 1: REJECT_FLOOR
    * X1 >= 9: REJECT_CEILING
    * 2 <= X1 <= 8: CONTINUE to Stage 2
  - Stage 2: Full Precision Evaluation (N = 20)
    * 0.35 <= p_hat <= 0.65: ADMIT
    * else: REJECT
  - Freezes admitted manifest with SHA-256 hash
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Tuple

sys.path.insert(0, os.path.abspath('.'))

from lerm.trace_purity import audit_calibration_trace, verify_calibration_cohort_purity, TracePurityViolation
from lerm.stats import wilson_score_interval, evaluate_calibration_admission

OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = os.environ.get("CALIBRATION_MODEL", "qwen2.5-coder:1.5b")
MASTER_SEED = 20260921
CALIBRATION_SEED_BASE = (MASTER_SEED + 500) % 100000  # 61421 per Protocol 05


DEFAULT_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
DEFAULT_NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "2048"))
DEFAULT_NUM_THREAD = int(os.environ.get("OLLAMA_NUM_THREAD", "4"))


def call_ollama(
    prompt: str,
    seed: int,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
    num_predict: int = DEFAULT_NUM_PREDICT,
    num_thread: int = DEFAULT_NUM_THREAD,
    max_retries: int = 2,
) -> str:
    """Calls local Ollama with pinned seed and temperature 0.7, with retry on transient infrastructure timeout."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "seed": seed,
            "num_predict": num_predict,
            "num_thread": num_thread,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("response", "")
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                print(f"[Ollama Warning] Attempt {attempt} failed ({e}), retrying in 5s...", flush=True)
                time.sleep(5)
    raise RuntimeError(f"Ollama infrastructure call failed (model={model}, seed={seed}): {last_err}") from last_err



def extract_python_code(text: str) -> str:
    """Extracts python code block from model response."""
    match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match_any = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match_any:
        return match_any.group(1).strip()
    return text.strip()


def run_single_calibration_trial(
    task_id: str,
    patch_content: str,
    trial_idx: int,
    seed: int,
    repo_dir: str = "mewwts__addict.75284f95",
    model: str = DEFAULT_MODEL,
    num_thread: int = DEFAULT_NUM_THREAD,
) -> tuple[bool, dict[str, Any]]:
    """Runs a single-shot calibration trial."""
    t0 = time.perf_counter()
    run_id = f"CALIB-{task_id}-t{trial_idx:02d}-s{seed}"
    
    # 1. Reset repo to clean state
    subprocess.run(["git", "checkout", "--", "."], cwd=repo_dir, capture_output=True, check=True)
    
    # 2. Apply task bug patch
    p_apply = subprocess.run(
        ["git", "apply", "--whitespace=nowarn"],
        input=patch_content,
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if p_apply.returncode != 0:
        raise RuntimeError(f"Failed to apply patch for {task_id}: {p_apply.stderr}")
        
    # Read the mutated file
    mutated_file = os.path.join(repo_dir, "addict", "addict.py")
    with open(mutated_file, "r", encoding="utf-8") as f:
        mutated_code = f.read()
        
    # 3. Construct single-shot prompt (Zero verifier diagnostics, Zero test output)
    prompt = (
        f"You are a Python expert reviewing the addict library.\n"
        f"The file `addict/addict.py` has an implementation bug in one of its methods.\n"
        f"Review the code and provide the complete corrected version of `addict/addict.py`.\n"
        f"Output ONLY the corrected Python code enclosed in a ```python block.\n\n"
        f"```python\n{mutated_code}\n```"
    )
    
    # 4. Generate repair attempt
    response = call_ollama(prompt, seed=seed, model=model, num_thread=num_thread)
    corrected_code = extract_python_code(response)
    
    # 5. Evaluate repair with ground-truth pytest
    success = False
    if corrected_code and len(corrected_code) > 50 and "class Dict" in corrected_code:
        with open(mutated_file, "w", encoding="utf-8") as f:
            f.write(corrected_code)
            
        p_test = subprocess.run(
            [sys.executable, "-m", "pytest", "test_addict.py", "-q"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=15,
        )
        success = (p_test.returncode == 0)
        
    # 6. Revert working copy to clean baseline
    subprocess.run(["git", "checkout", "--", "."], cwd=repo_dir, capture_output=True)
    dt = time.perf_counter() - t0
    
    # 7. Build Trace Record adhering to Gate A12
    record = {
        "run_id": run_id,
        "task_id": task_id,
        "condition": "single_shot_calibration",
        "data_role": "calibration",
        "attempts": 1,
        "turns_taken": 1,
        "verifier_calls": 0,
        "feedback_injected": False,
        "retry_count": 0,
        "success": success,
        "seed": seed,
        "model": model,
        "duration_s": round(dt, 3),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    
    # Gate A12 fail-closed audit
    errs = audit_calibration_trace(record)
    if errs:
        raise TracePurityViolation(f"Trace purity violated in {run_id}: {errs}")
        
    return success, record


def calibrate_task(
    cand: dict[str, Any],
    patch_content: str,
    task_idx: int,
    repo_dir: str = "mewwts__addict.75284f95",
    model: str = DEFAULT_MODEL,
    num_thread: int = DEFAULT_NUM_THREAD,
    on_trial_complete: Any = None,
) -> tuple[str, float, tuple[float, float], list[dict[str, Any]]]:
    """Calibrates a single task via 2-stage sequential screening (Protocol 06 §2)."""
    task_id = cand["task_id"]
    traces = []
    
    # --- STAGE 1: Preliminary Screen (N1 = 10) ---
    print(f"\n[{task_id}] Stage 1 Screening (N1 = 10)...", flush=True)
    s1_successes = 0
    for i in range(1, 11):
        seed = CALIBRATION_SEED_BASE + task_idx * 100 + i
        ok, rec = run_single_calibration_trial(
            task_id, patch_content, i, seed, repo_dir, model, num_thread=num_thread
        )
        traces.append(rec)
        if on_trial_complete:
            on_trial_complete(rec)
        if ok:
            s1_successes += 1
        print(f"  Trial {i:02d} (seed {seed}): {'PASS' if ok else 'FAIL'} (duration {rec['duration_s']}s) | Cumulative: {s1_successes}/{i}", flush=True)
        
    # Stage 1 Stopping Rule
    if s1_successes <= 1:
        ci = wilson_score_interval(s1_successes, 10)
        p_hat = s1_successes / 10.0
        print(f"[{task_id}] Stage 1 Result: REJECT_FLOOR (X1={s1_successes}/10 <= 1, p_hat={p_hat:.2f})", flush=True)
        return "REJECT_FLOOR", p_hat, ci, traces
        
    if s1_successes >= 9:
        ci = wilson_score_interval(s1_successes, 10)
        p_hat = s1_successes / 10.0
        print(f"[{task_id}] Stage 1 Result: REJECT_CEILING (X1={s1_successes}/10 >= 9, p_hat={p_hat:.2f})", flush=True)
        return "REJECT_CEILING", p_hat, ci, traces
        
    # --- STAGE 2: Full Precision Evaluation (N = 20 total) ---
    print(f"[{task_id}] Continuing to Stage 2 (X1={s1_successes}/10 in [2, 8])...", flush=True)
    s2_successes = 0
    for i in range(11, 21):
        seed = CALIBRATION_SEED_BASE + task_idx * 100 + i
        ok, rec = run_single_calibration_trial(
            task_id, patch_content, i, seed, repo_dir, model, num_thread=num_thread
        )
        traces.append(rec)
        if on_trial_complete:
            on_trial_complete(rec)
        if ok:
            s2_successes += 1
        print(f"  Trial {i:02d} (seed {seed}): {'PASS' if ok else 'FAIL'} (duration {rec['duration_s']}s) | Cumulative: {s1_successes + s2_successes}/{i}", flush=True)
        
    total_x = s1_successes + s2_successes
    p_hat = total_x / 20.0
    ci = wilson_score_interval(total_x, 20)
    
    # Guardband Admission Rule: 0.35 <= p_hat <= 0.65 (7 <= X <= 13)
    if 0.35 <= p_hat <= 0.65:
        decision = "ADMIT"
        print(f"[{task_id}] Stage 2 Result: ADMIT (X={total_x}/20, p_hat={p_hat:.2f}, 95% CI=[{ci[0]:.2f}, {ci[1]:.2f}])", flush=True)
    else:
        decision = "REJECT_OUT_OF_BAND"
        print(f"[{task_id}] Stage 2 Result: REJECT_OUT_OF_BAND (X={total_x}/20, p_hat={p_hat:.2f}, 95% CI=[{ci[0]:.2f}, {ci[1]:.2f}])", flush=True)
        
    return decision, p_hat, ci, traces


def run_calibration(
    candidates_jsonl: str = "data/phase-d/candidates.jsonl",
    patches_dir: str = "data/phase-d/patches",
    out_dir: str = "data/phase-d",
    max_tasks: int = 30,
    model: str = DEFAULT_MODEL,
    num_thread: int = DEFAULT_NUM_THREAD,
    resume: bool = True,
):
    print("=== LERM EXP-LOOP-003 Phase D Calibration Runner ===", flush=True)
    print(f"Model: {model} | Seed Base: {CALIBRATION_SEED_BASE} | Max Tasks: {max_tasks} | Threads: {num_thread}", flush=True)
    
    with open(candidates_jsonl, "r", encoding="utf-8") as f:
        candidates = [json.loads(line) for line in f][:max_tasks]
        
    traces_path = os.path.join(out_dir, "calibration_traces.jsonl")
    calib_summary_path = os.path.join(out_dir, "calibration_summary.json")
    
    all_traces = []
    calibration_results = []
    completed_task_ids = set()
    
    if resume and os.path.exists(calib_summary_path) and os.path.exists(traces_path):
        try:
            with open(calib_summary_path, "r", encoding="utf-8") as f:
                calibration_results = json.load(f)
            completed_task_ids = {r["task_id"] for r in calibration_results}
            with open(traces_path, "r", encoding="utf-8") as f:
                raw_traces = [json.loads(line) for line in f if line.strip()]
            all_traces = [t for t in raw_traces if t.get("task_id") in completed_task_ids]
            with open(traces_path, "w", encoding="utf-8") as tf:
                for t in all_traces:
                    tf.write(json.dumps(t) + "\n")
            pruned_count = len(raw_traces) - len(all_traces)
            print(f"[Resume] Found {len(completed_task_ids)} previously completed tasks ({len(all_traces)} traces). Pruned {pruned_count} incomplete trailing traces.", flush=True)
        except Exception as e:
            print(f"[Resume Warning] Could not load existing summary/traces ({e}), starting clean.", flush=True)
            all_traces = []
            calibration_results = []
            completed_task_ids = set()
            
    def append_trace(rec: dict[str, Any]) -> None:
        with open(traces_path, "a", encoding="utf-8") as tf:
            tf.write(json.dumps(rec) + "\n")
            tf.flush()

    for idx, cand in enumerate(candidates, start=1):
        task_id = cand["task_id"]
        if task_id in completed_task_ids:
            print(f"[{task_id}] Skipping already completed task.", flush=True)
            continue
            
        patch_file = os.path.join(patches_dir, f"{task_id}.diff")
        with open(patch_file, "r", encoding="utf-8") as f:
            patch_content = f.read()
            
        decision, p_hat, ci, traces = calibrate_task(
            cand, patch_content, idx, model=model, num_thread=num_thread, on_trial_complete=append_trace
        )
        all_traces.extend(traces)
        
        result_entry = {
            "task_id": task_id,
            "mutation_rule": cand["mutation_rule"],
            "decision": decision,
            "p_hat": round(p_hat, 3),
            "ci_95": [round(ci[0], 3), round(ci[1], 3)],
            "trials_run": len(traces),
            "successes": sum(1 for t in traces if t["success"]),
        }
        calibration_results.append(result_entry)
        completed_task_ids.add(task_id)
        
        # Persist summary immediately after each task
        with open(calib_summary_path, "w", encoding="utf-8") as f:
            json.dump(calibration_results, f, indent=2)
            f.flush()
            
    # Audit entire trace cohort purity (Gate A12)
    verify_calibration_cohort_purity(all_traces)
    print(f"\n[Gate A12] Successfully audited {len(all_traces)} calibration traces for 100% purity.", flush=True)
    
    # Save admitted primary manifest if any admitted
    admitted_candidates = []
    for cand in candidates:
        task_res = next((r for r in calibration_results if r["task_id"] == cand["task_id"]), None)
        if task_res and task_res["decision"] == "ADMIT":
            c_admit = dict(cand)
            c_admit["data_role"] = "primary"
            c_admit["primary_exp_loop_003_eligible"] = True
            admitted_candidates.append(c_admit)
            
    admitted_manifest_path = os.path.join(out_dir, "admitted_primary_manifest.yaml")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    lines = [
        'schema_version: "1.0.0"',
        'manifest_id: "EXP-LOOP-003-ADMITTED-PRIMARY"',
        f'calibrated_at: "{now_iso}"',
        f'calibration_model: "{model}"',
        f'total_admitted: {len(admitted_candidates)}',
        'tasks:',
    ]
    for c in admitted_candidates:
        lines.append(f'  - id: "{c["task_id"]}"')
        lines.append(f'    mutation_rule: "{c["mutation_rule"]}"')
        lines.append(f'    candidate_content_hash: "{c["candidate_content_hash"]}"')
        lines.append(f'    data_role: "primary"')
        lines.append(f'    primary_exp_loop_003_eligible: true')
        
    with open(admitted_manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
        
    # Manifest SHA-256
    h = hashlib.sha256()
    with open(admitted_manifest_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    manifest_sha = h.hexdigest()
    
    with open(os.path.join(out_dir, "ADMITTED_MANIFEST_SHA256.txt"), "w", encoding="utf-8") as f:
        f.write(f"{manifest_sha}  admitted_primary_manifest.yaml\n")
        
    print(f"\nCalibration Complete:", flush=True)
    print(f"  Total Candidates Evaluated: {len(calibration_results)}", flush=True)
    print(f"  Total Admitted: {len(admitted_candidates)}", flush=True)
    print(f"  Admitted Manifest SHA-256: {manifest_sha}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tasks", type=int, default=30)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--threads", type=int, default=DEFAULT_NUM_THREAD)
    parser.add_argument("--no-resume", action="store_true", default=False)
    args = parser.parse_args()
    
    run_calibration(
        max_tasks=args.max_tasks,
        model=args.model,
        num_thread=args.threads,
        resume=(not args.no_resume),
    )
