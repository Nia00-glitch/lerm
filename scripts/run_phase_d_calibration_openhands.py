#!/usr/bin/env python3
"""Phase D Difficulty Calibration Runner under OpenHands (Protocol v2 & DECISION-0006).

Evaluates candidate tasks under autonomous single-turn OpenHands execution using
openrouter/thinkingmachines/inkling-small:free.

Features:
- Paced execution (5s sleep between actions/trials) to strictly respect 20 RPM limit.
- Daily quota discipline: Tracks cumulative LLM calls and caps daily execution at 15 trials (~150 LLM calls)
  to preserve the 200 RPD OpenRouter free-tier quota and the ₹0 budget constraint.
- Stage 1 Sequential Screen (N1 = 10):
    * X1 <= 1: REJECT_FLOOR
    * X1 >= 9: REJECT_CEILING
    * 2 <= X1 <= 8: CONTINUE to Stage 2
- Stage 2 Full Precision (N = 20 total):
    * 0.35 <= p_hat <= 0.65: ADMIT
    * else: REJECT_OUT_OF_BAND
- Gate A12 Trace Purity audit on every trial.
- Automated update of calibration summary, rejection log, and admitted primary manifest with SHA-256 freezing.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import yaml

sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

from lerm.adapters.openhands import OpenHandsAgent, _request
from lerm.trace_purity import audit_calibration_trace, verify_calibration_cohort_purity
from lerm.stats import wilson_score_interval
from lerm.calibration import (
    evaluate_stage1_screen,
    evaluate_stage2_admission,
    compute_task_metrics,
    generate_admitted_manifest_yaml,
)

CONTAINER_NAME = "oh-agent-server-1QdXehKsSEZITvWvP0Tp1C"
WORKDIR = "/workspace/project"
MODEL_NAME = "openrouter/thinkingmachines/inkling-small:free"
TRACES_PATH = "data/phase-d/calibration_traces_inkling.jsonl"
SUMMARY_PATH = "data/phase-d/calibration_summary_inkling.json"
DAILY_STATE_PATH = "state/daily_calibration_quota.json"
REJECTION_LOG_PATH = "data/phase-d/rejection_log_inkling.json"
ADMITTED_MANIFEST_PATH = "data/phase-d/admitted_primary_manifest.yaml"
ADMITTED_SHA_PATH = "data/phase-d/ADMITTED_MANIFEST_SHA256.txt"
MAX_DAILY_TRIALS = 15  # ~150 LLM calls, staying safely below 200 RPD
MASTER_SEED = 20260921
CALIBRATION_SEED_BASE = (MASTER_SEED + 500) % 100000  # 61421


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
        raise RuntimeError(f"Baseline reset failed: {res.stdout} {res.stderr}")


def apply_patch(diff_path: str):
    unpause()
    with open(diff_path, "rb") as f:
        diff_bytes = f.read().replace(b"\r\n", b"\n")
    proc = subprocess.Popen(
        ["docker", "exec", "-u", "0", "-i", CONTAINER_NAME, "sh", "-c", f"git -C {WORKDIR} apply --whitespace=nowarn"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate(input=diff_bytes)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to apply patch {diff_path}: {stderr.decode()}")
    subprocess.run(
        ["docker", "exec", "-u", "0", CONTAINER_NAME, "sh", "-c", f"chown openhands:openhands {WORKDIR}/addict/addict.py"],
        check=True
    )
    res = subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "python3", "-m", "pytest", f"{WORKDIR}/test_addict.py", "-q"],
        capture_output=True, text=True
    )
    if res.returncode == 0:
        raise RuntimeError(f"Precondition failed: tests passed after applying bug patch {diff_path}!")


def get_daily_trials_run() -> int:
    today_str = datetime.date.today().isoformat()
    if os.path.exists(DAILY_STATE_PATH):
        try:
            with open(DAILY_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") == today_str:
                return data.get("trials_run", 0)
        except Exception:
            pass
    return 0


def increment_daily_trials_run() -> int:
    today_str = datetime.date.today().isoformat()
    current = get_daily_trials_run() + 1
    os.makedirs(os.path.dirname(DAILY_STATE_PATH), exist_ok=True)
    with open(DAILY_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"date": today_str, "trials_run": current}, f, indent=2)
    return current


def load_all_traces() -> list[dict[str, Any]]:
    traces = []
    if os.path.exists(TRACES_PATH):
        with open(TRACES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    traces.append(json.loads(line))
    return traces


def persist_summary_and_artifacts(
    manifest_tasks_by_id: dict[str, Any],
    max_daily_trials: int = MAX_DAILY_TRIALS,
) -> dict[str, Any]:
    """Computes and writes summary, rejection log, and admitted manifest."""
    traces = load_all_traces()
    verify_calibration_cohort_purity(traces)

    traces_by_task: dict[str, list[dict[str, Any]]] = {}
    for t in traces:
        task_id = t["task_id"]
        traces_by_task.setdefault(task_id, []).append(t)

    summary_tasks: dict[str, Any] = {}
    admitted_tasks: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []

    for task_id, task_traces in traces_by_task.items():
        metrics = compute_task_metrics(task_traces)
        meta = manifest_tasks_by_id.get(task_id, {})
        metrics["constituent_tasks"] = meta.get("constituent_tasks", [])
        metrics["constituent_functions"] = meta.get("constituent_functions", [])
        metrics["constituent_rules"] = meta.get("constituent_rules", [])
        metrics["admission_band"] = [0.35, 0.65]

        summary_tasks[task_id] = metrics

        overall = metrics.get("overall_verdict")
        if overall == "ADMIT":
            admitted_entry = dict(meta)
            admitted_entry["id"] = task_id
            admitted_entry["p_hat"] = metrics["p_hat"]
            admitted_entry["wilson_ci_95"] = metrics["wilson_ci_95"]
            admitted_tasks.append(admitted_entry)
        elif overall in ("REJECT_FLOOR", "REJECT_CEILING", "REJECT_OUT_OF_BAND_HARD", "REJECT_OUT_OF_BAND_EASY"):
            rejections.append({
                "task_id": task_id,
                "rejection_reason": overall,
                "stage": 1 if overall in ("REJECT_FLOOR", "REJECT_CEILING") else 2,
                "n_trials": metrics["n_trials"],
                "successes": metrics["successes"],
                "p_hat": metrics["p_hat"],
                "wilson_ci_95": metrics["wilson_ci_95"],
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })

    trials_today = get_daily_trials_run()
    quota_status = "EXHAUSTED_SAFELY_FOR_TODAY" if trials_today >= max_daily_trials else "ACTIVE"

    summary_data = {
        "protocol": "Protocol 06 §2 / DECISION-0006",
        "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": MODEL_NAME,
        "harness": "OpenHands agent-server single-turn",
        "tasks": summary_tasks,
        "daily_trials_completed": trials_today,
        "daily_quota_cap": max_daily_trials,
        "daily_quota_status": quota_status,
    }

    os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Persist rejection log
    if rejections:
        os.makedirs(os.path.dirname(REJECTION_LOG_PATH), exist_ok=True)
        with open(REJECTION_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(rejections, f, indent=2)

    # Persist admitted manifest if any admitted
    if admitted_tasks:
        manifest_yaml = generate_admitted_manifest_yaml(admitted_tasks, MODEL_NAME)
        with open(ADMITTED_MANIFEST_PATH, "w", encoding="utf-8") as f:
            f.write(manifest_yaml)

        # Freeze hash
        h = hashlib.sha256()
        with open(ADMITTED_MANIFEST_PATH, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        manifest_sha = h.hexdigest()
        with open(ADMITTED_SHA_PATH, "w", encoding="utf-8") as f:
            f.write(f"{manifest_sha}  admitted_primary_manifest.yaml\n")

    return summary_data


def run_single_calibration_trial(
    agent: OpenHandsAgent,
    task_id: str,
    diff_path: str,
    trial_idx: int,
    seed: int,
    timeout_s: float = 180.0,
) -> tuple[bool, dict]:
    """Runs a single-shot calibration trial conforming to DECISION-0006 and Gate A12."""
    t0 = time.time()
    reset_repo()
    apply_patch(diff_path)

    agent.activate_profile("pinned_inkling")
    instruction = (
        "You are working on the Python addict library in /workspace/project. "
        "The file addict/addict.py has implementation bugs in its code. "
        "Inspect the repository and fix the bugs in addict/addict.py so all tests pass."
    )

    cid = None
    for startup_attempt in range(3):
        try:
            cid = agent.start_conversation(
                instruction=instruction,
                model=MODEL_NAME,
                workspace="",
                extra={"sandbox_id": CONTAINER_NAME}
            )
            if cid:
                break
        except Exception:
            if startup_attempt == 2:
                raise
            time.sleep(4.0)

    send_body = {
        "role": "user",
        "content": [{"type": "text", "text": instruction}],
        "run": True
    }

    for attempt in range(5):
        time.sleep(2.0)
        unpause()
        try:
            status, _ = _request(
                f"{agent.base_url}/api/v1/app-conversations/{cid}/send-message",
                method="POST", body=send_body, timeout=60.0
            )
            if status < 400:
                break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3.0)

    deadline = time.time() + timeout_s
    exec_state = "unknown"
    actions_taken = 0
    poll_count = 0

    while time.time() < deadline:
        time.sleep(4.0)
        unpause()
        poll_count += 1
        try:
            st, body = _request(f"{agent.base_url}/api/v1/app-conversations?ids={cid}")
            if st < 400 and isinstance(body, list) and body:
                meta = body[0]
                exec_state = str(meta.get("execution_status") or meta.get("status") or "").lower()
                # Query events when status suggests completion, or periodically every 4 polls (~16s)
                if exec_state in {"stopped", "finished", "error", "completed", "idle", "paused"} or poll_count % 4 == 0:
                    events = agent.events(cid)
                    action_events = [e for e in events if e.get("kind") in ("ActionEvent", "Action") or e.get("action") is not None]
                    actions_taken = len(action_events)
                    has_agent_turn = any(e.get("source") == "agent" for e in events)
                    if has_agent_turn and exec_state in {"stopped", "finished", "error", "completed", "idle", "paused"}:
                        break
        except Exception:
            pass

    # Final event inspection to ensure complete action count
    try:
        events = agent.events(cid)
        action_events = [e for e in events if e.get("kind") in ("ActionEvent", "Action") or e.get("action") is not None]
        actions_taken = len(action_events)
    except Exception:
        pass

    dt = time.time() - t0

    # Ground truth evaluation
    unpause()
    res = subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "python3", "-m", "pytest", f"{WORKDIR}/test_addict.py", "-q"],
        capture_output=True, text=True
    )
    success = (res.returncode == 0)
    reset_repo()

    # Gate A12 trace record
    record = {
        "run_id": f"CALIB-OH-{task_id}-t{trial_idx:02d}-s{seed}",
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
        "model": MODEL_NAME,
        "duration_s": round(dt, 2),
        "actions_taken": actions_taken,
        "final_state": exec_state,
        "conversation_id": cid,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    # Audit purity
    errors = audit_calibration_trace(record)
    if errors:
        raise RuntimeError(f"Trace purity audit failed for {record['run_id']}: {errors}")

    return success, record


def run_calibration_cohort(
    task_ids: list[str],
    manifest_path: str = "data/phase-d/compound_manifest.yaml",
    patches_dir: str = "data/phase-d/patches",
    max_trials_today: int = MAX_DAILY_TRIALS,
) -> None:
    agent = OpenHandsAgent()
    agent.activate_profile("pinned_inkling")
    os.makedirs(os.path.dirname(TRACES_PATH), exist_ok=True)

    manifest_tasks_by_id: dict[str, Any] = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            m = yaml.safe_load(f)
        for t in m.get("tasks", []):
            manifest_tasks_by_id[t["id"]] = t

    trials_done_today = get_daily_trials_run()
    print(f"[Calibration Runner] Date: {datetime.date.today().isoformat()}, Trials run today: {trials_done_today}/{max_trials_today}")

    if trials_done_today >= max_trials_today:
        print(f"[Quota Halt] Daily trial limit ({max_trials_today}) reached. Halting to preserve 200 RPD OpenRouter quota per DECISION-0006.")
        persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)
        return

    # Load existing traces
    existing_traces = load_all_traces()
    existing_trials_by_task: dict[str, set[int]] = {}
    for t in existing_traces:
        trial_num = int(t["run_id"].split("-t")[1].split("-s")[0])
        existing_trials_by_task.setdefault(t["task_id"], set()).add(trial_num)

    for task_idx, task_id in enumerate(task_ids):
        diff_path = os.path.join(patches_dir, f"{task_id}.diff")
        if not os.path.exists(diff_path):
            print(f"Warning: Patch file {diff_path} not found. Skipping {task_id}.")
            continue

        print(f"\n=======================================================")
        print(f"Calibrating Candidate Task: {task_id}")
        print(f"=======================================================")

        executed_trials = existing_trials_by_task.get(task_id, set())

        # STAGE 1: Trials 0..9 (N1 = 10)
        stage1_needed = [i for i in range(10) if i not in executed_trials]
        for trial_idx in stage1_needed:
            trials_done_today = get_daily_trials_run()
            if trials_done_today >= max_trials_today:
                print(f"\n[Daily Quota Reached] Executed {trials_done_today} trials today. Halting safely.")
                persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)
                return

            seed = CALIBRATION_SEED_BASE + trial_idx * 100 + task_idx
            print(f"  Running Stage 1 Trial {trial_idx+1}/10 (seed={seed}, daily_trial={trials_done_today+1}/{max_trials_today})...")

            succ, record = run_single_calibration_trial(agent, task_id, diff_path, trial_idx, seed)
            increment_daily_trials_run()
            executed_trials.add(trial_idx)
            existing_trials_by_task.setdefault(task_id, set()).add(trial_idx)

            with open(TRACES_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            print(f"  --> Trial {trial_idx+1} result: {'PASS' if succ else 'FAIL'} (Actions: {record['actions_taken']}, Duration: {record['duration_s']}s)")
            persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)
            time.sleep(5.0)

        # Evaluate Stage 1 Screen
        all_traces = load_all_traces()
        task_traces = [t for t in all_traces if t["task_id"] == task_id]
        if len(task_traces) < 10:
            print(f"  Stage 1 incomplete for {task_id} ({len(task_traces)}/10 trials). Continuing.")
            continue

        s1_successes = sum(1 for t in task_traces[:10] if t["success"])
        s1_verdict = evaluate_stage1_screen(s1_successes, 10)
        print(f"  Stage 1 Screen: {s1_verdict} ({s1_successes}/10 successes)")

        if s1_verdict in ("REJECT_FLOOR", "REJECT_CEILING"):
            print(f"  --> Task {task_id} rejected at Stage 1 ({s1_verdict}). Stopping candidate.")
            persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)
            continue

        # STAGE 2: Trials 10..19 (N2 = 10, Total N = 20)
        print(f"  Stage 1 Passed! Advancing to Stage 2 Precision Evaluation (Trials 11-20)...")
        stage2_needed = [i for i in range(10, 20) if i not in executed_trials]
        for trial_idx in stage2_needed:
            trials_done_today = get_daily_trials_run()
            if trials_done_today >= max_trials_today:
                print(f"\n[Daily Quota Reached] Executed {trials_done_today} trials today. Halting safely.")
                persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)
                return

            seed = CALIBRATION_SEED_BASE + trial_idx * 100 + task_idx
            print(f"  Running Stage 2 Trial {trial_idx+1}/20 (seed={seed}, daily_trial={trials_done_today+1}/{max_trials_today})...")

            succ, record = run_single_calibration_trial(agent, task_id, diff_path, trial_idx, seed)
            increment_daily_trials_run()
            executed_trials.add(trial_idx)
            existing_trials_by_task.setdefault(task_id, set()).add(trial_idx)

            with open(TRACES_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            print(f"  --> Trial {trial_idx+1} result: {'PASS' if succ else 'FAIL'} (Actions: {record['actions_taken']}, Duration: {record['duration_s']}s)")
            persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)
            time.sleep(5.0)

        # Stage 2 Evaluation
        all_traces = load_all_traces()
        task_traces = [t for t in all_traces if t["task_id"] == task_id]
        if len(task_traces) == 20:
            total_succ = sum(1 for t in task_traces if t["success"])
            decision, p_hat, ci = evaluate_stage2_admission(total_succ, 20)
            print(f"\n  [Stage 2 Admission Verdict for {task_id}]")
            print(f"  Decision: {decision}")
            print(f"  Successes: {total_succ}/20 (p_hat = {p_hat:.4f})")
            print(f"  95% Wilson CI: [{ci[0]:.4f}, {ci[1]:.4f}]")
            persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)

    print("\n[Calibration Runner] Cohort evaluation complete for today.")
    persist_summary_and_artifacts(manifest_tasks_by_id, max_daily_trials=max_trials_today)


def main():
    parser = argparse.ArgumentParser(description="Phase D OpenHands Difficulty Calibration Runner")
    parser.add_argument("--tasks", nargs="+", default=None)
    parser.add_argument("--manifest", default="data/phase-d/compound_manifest.yaml")
    parser.add_argument("--max-daily-trials", type=int, default=MAX_DAILY_TRIALS)
    args = parser.parse_args()

    if args.tasks:
        tasks = args.tasks
    elif os.path.exists(args.manifest):
        with open(args.manifest, "r", encoding="utf-8") as f:
            m = yaml.safe_load(f)
        tasks = [t["id"] for t in m.get("tasks", [])]
    else:
        tasks = ["COMP-001"]

    run_calibration_cohort(
        task_ids=tasks,
        manifest_path=args.manifest,
        max_trials_today=args.max_daily_trials,
    )


if __name__ == "__main__":
    main()
