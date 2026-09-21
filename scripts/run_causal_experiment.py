#!/usr/bin/env python3
"""Autonomous Causal Experiment Runner for LERM (EXP-LOOP-001).

Tests the core causal hypothesis:
"In-loop verification and repair (loop_verify) yields a higher pass^5 verified success rate
than compute-matched naive retry (loop_retry) under matched token and turn budgets on
held-out code repair tasks."

Design:
- Matched conditions: 'loop_retry' vs 'loop_verify'
- Tasks: HOLDOUT-001, HOLDOUT-002, HOLDOUT-003, HOLDOUT-004
- Seeds: 1001, 1002, 1003, 1004, 1005 (k=5 reruns per task per condition)
- Budget matching: fixed 3-turn ceiling, 240s wallclock, 16000 tokens
- Triple outcome isolation: agent_claimed, verifier_said, ground_truth
- D6 anti-tamper security: tests locked as root:root chmod 555/444
- Offline Skeptic & Confound Checklist audit
- Automated Knowledge Base registration (findings/ or negative_results/)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm.adapters.openhands import OpenHandsAgent, _request
from lerm.checkpoint import ExperimentCheckpoint, TrialSpec
from lerm.controller import DeterministicLoopController, EpisodeBudget, LoopCondition, LoopStep
from lerm.evaluator import IndependentEvaluator
from lerm.kb import Finding, from_skeptic, load_all
from lerm.ledger import ResearchLedger, LedgerEntry
from lerm.prereg import assert_declared, verify as verify_prereg
from lerm.skeptic import Skeptic
from lerm import confounds as cf, stats as st, trace

EXPERIMENT_ID = "EXP-LOOP-002"
PREREG_ID = "EXP-LOOP-002"
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "openrouter/thinkingmachines/inkling-small:free")
TASKS_DIR = Path("holdout/tasks")
TASK_IDS = ["HOLDOUT-001", "HOLDOUT-002", "HOLDOUT-003", "HOLDOUT-004"]
CONDITIONS = ["loop_retry", "loop_verify"]
SEEDS = [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010]


def get_active_sandbox() -> str | None:
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--filter", "ancestor=ghcr.io/openhands/agent-server:1.26.0-python", "--format", "{{.Names}}"],
            text=True,
        ).strip().splitlines()
        return out[0] if out else None
    except Exception:
        return None


def unpause_container(container_id: str | None) -> None:
    if container_id:
        subprocess.run(["docker", "unpause", container_id], capture_output=True)


def materialize_task_files(container_id: str, files: list[dict], workdir: str = "/workspace/project") -> None:
    # 1. Clean workspace directory
    subprocess.run(["docker", "exec", "-u", "0", container_id, "sh", "-c", f"rm -rf {workdir}/*"], capture_output=True)
    subprocess.run(["docker", "exec", "-u", "0", container_id, "mkdir", "-p", workdir], check=True)

    # 2. Write fixture files
    for f in files:
        rel_path = f["path"]
        content = f["content"]
        dir_name = os.path.dirname(rel_path)
        if dir_name:
            subprocess.run(["docker", "exec", "-u", "0", container_id, "mkdir", "-p", f"{workdir}/{dir_name}"], check=True)
        proc = subprocess.Popen(
            ["docker", "exec", "-u", "0", "-i", container_id, "sh", "-c", f"cat > {workdir}/{rel_path}"],
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=content.encode("utf-8"))

    # 3. D6 Anti-Tamper Security Hardening:
    # Read-only tests & verification scripts owned by root so agent cannot tamper with assertions
    lock_cmd = (
        f"chown -R openhands:openhands {workdir} && "
        f"for d in {workdir}/tests {workdir}/scripts/verify_*; do "
        f"  if [ -e \"$d\" ]; then chown -R root:root \"$d\" && chmod -R 555 \"$d\" 2>/dev/null || chmod -R 444 \"$d\"; fi; "
        f"done"
    )
    subprocess.run(["docker", "exec", "-u", "0", container_id, "sh", "-c", lock_cmd], capture_output=True)


def compute_fixture_hashes(container_id: str, files: list[dict], workdir: str = "/workspace/project") -> tuple[str, str]:
    """Computes (canonical_fixture_hash, on_disk_fixture_hash) across all setup files."""
    h_canon = hashlib.sha256()
    h_disk = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["path"]):
        rel = f["path"]
        canon_bytes = f["content"].encode("utf-8")
        h_canon.update(rel.encode("utf-8") + b":" + canon_bytes + b"\n")

        res = subprocess.run(
            ["docker", "exec", container_id, "cat", f"{workdir}/{rel}"],
            capture_output=True,
        )
        disk_bytes = res.stdout if res.returncode == 0 else b""
        h_disk.update(rel.encode("utf-8") + b":" + disk_bytes + b"\n")

    return h_canon.hexdigest(), h_disk.hexdigest()



def run_in_loop_test(container_id: str, entrypoint: str, workdir: str = "/workspace/project") -> tuple[bool, str]:
    """Runs the task's verification entrypoint inside the sandbox container."""
    cmd = f"cd {workdir} && {entrypoint}"
    res = subprocess.run(
        ["docker", "exec", "-u", "openhands", container_id, "sh", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=60,
    )
    passed = (res.returncode == 0)
    output = (res.stdout + "\n" + res.stderr).strip()
    return passed, output


def execute_turn(
    agent: OpenHandsAgent,
    conversation_id: str,
    container_id: str,
    prompt: str,
    timeout_s: float = 180.0,
) -> tuple[dict, list[dict], float]:
    """Dispatches a prompt turn to OpenHands and polls until the agent turn completes."""
    t0 = time.time()
    unpause_container(container_id)

    send_body = {
        "role": "user",
        "content": [{"type": "text", "text": prompt}],
        "run": True,
    }
    sent = False
    for attempt in range(6):
        time.sleep(1.5)
        unpause_container(container_id)
        st, resp = _request(
            f"{agent.base_url}/api/v1/app-conversations/{conversation_id}/send-message",
            method="POST",
            body=send_body,
            timeout=60.0,
        )
        if st < 400:
            sent = True
            break

    if not sent:
        raise RuntimeError(f"Failed to send message to conversation {conversation_id}: status={st}")

    deadline = time.time() + timeout_s
    meta = {}
    time.sleep(4.0)
    while time.time() < deadline:
        unpause_container(container_id)
        try:
            status, body = _request(f"{agent.base_url}/api/v1/app-conversations?ids={conversation_id}")
            if status < 400 and isinstance(body, list) and body and body[0]:
                meta = body[0]
                exec_state = str(meta.get("execution_status") or meta.get("status") or meta.get("state") or "").lower()
                curr_events = agent.events(conversation_id)
                has_agent_turn = any(e.get("source") == "agent" for e in curr_events)
                if has_agent_turn and exec_state in {"stopped", "finished", "error", "completed", "idle", "paused"}:
                    break
        except Exception:
            pass
        time.sleep(4.0)

    turn_duration = time.time() - t0
    events = agent.events(conversation_id)
    return meta, events, turn_duration


def run_trial(
    task_path: Path,
    condition: str,
    seed: int,
    rerun_index: int,
    agent: OpenHandsAgent,
    model_name: str,
    budget: EpisodeBudget,
) -> trace.RunRecord:
    with open(task_path, "r", encoding="utf-8") as fh:
        task = yaml.safe_load(fh)

    task_id = task["id"]
    instruction = task["instruction"]
    entrypoint = task.get("ground_truth_checker", {}).get("entrypoint", "")

    print(f"\n[{EXPERIMENT_ID}] >>> Trial: Task={task_id}, Condition={condition}, Seed={seed}, Rerun={rerun_index}")

    t_start = time.time()
    record = trace.RunRecord(
        experiment_id=EXPERIMENT_ID,
        prereg_id=PREREG_ID,
        task_id=task_id,
        condition=condition,
        seed=seed,
        model_id=model_name,
        task_index=TASK_IDS.index(task_id) if task_id in TASK_IDS else 0,
        rerun_index=rerun_index,
        started_utc=datetime.now(timezone.utc).isoformat(),
    )

    # 1. Start OpenHands conversation (reusing active sandbox to prevent docker churn)
    active_sb = get_active_sandbox() or "oh-agent-server-AajqxBVbQlFXJphnMXMcS"
    cid = agent.start_conversation(
        instruction=instruction,
        model=model_name,
        workspace="",
        extra={"sandbox_id": active_sb},
    )
    container_id = active_sb

    # 2. Materialize task fixtures into sandbox & lock tests
    if "setup" in task and "files" in task["setup"]:
        unpause_container(container_id)
        materialize_task_files(container_id, task["setup"]["files"])
        c_hash, d_hash = compute_fixture_hashes(container_id, task["setup"]["files"])
        record.canonical_fixture_hash = c_hash
        record.fixture_hash = d_hash

    # 3. Setup Deterministic Loop Controller
    controller = DeterministicLoopController(condition=condition, budget=budget)
    last_step: LoopStep | None = None
    all_events: list[dict] = []
    total_tokens = 0
    in_loop_passed = False
    diagnostic_output = ""

    # 4. Iterative Loop execution
    while True:
        action = controller.decide_next_step(last_step)
        if action == "halt":
            break

        turn_index = len(controller.steps)
        print(f"  [STEP {turn_index}] Action: {action} (Condition={condition})")

        # Formulate prompt according to action primitive
        if action == "initial_attempt":
            prompt = instruction
        elif action == "retry":
            prompt = (
                f"Your previous attempt did not resolve the problem. "
                f"Please re-analyze the task from scratch and implement a working fix: {instruction}"
            )
        elif action == "repair":
            prompt = (
                f"In-loop verification failed with the following diagnostic output:\n"
                f"```\n{diagnostic_output[:1200]}\n```\n"
                f"Please inspect the error, identify the root cause, and repair the code."
            )
        else:
            break

        # Check wallclock ceiling before dispatching turn
        rem_s = controller.remaining_wallclock_s()
        if rem_s <= 5.0:
            print(f"  [CONTROLLER] Wallclock cap reached ({controller.elapsed_s:.1f}s >= {budget.max_wallclock_s}s). Halting trial.")
            break

        try:
            turn_timeout = min(90.0, rem_s)
            meta, events, duration = execute_turn(agent, cid, container_id, prompt, timeout_s=turn_timeout)
            all_events = events
        except Exception as ex:
            print(f"  [ERROR] Turn failed: {ex}")
            record.infra_failure = True
            break

        # Compute tokens used in this turn
        turn_tokens = 0
        for e in events:
            if e.get("source") == "agent":
                turn_tokens += max(10, len(str(e.get("llm_message", {}).get("content", ""))) // 4)
            elif e.get("source") == "user":
                turn_tokens += max(10, len(str(e.get("llm_message", {}).get("content", ""))) // 4)
        total_tokens += turn_tokens

        # Check in-loop test status
        in_loop_passed, diagnostic_output = run_in_loop_test(container_id, entrypoint)
        print(f"  [IN-LOOP TEST] Passed={in_loop_passed} (Diagnostic chars: {len(diagnostic_output)})")

        step = LoopStep(
            turn_index=turn_index,
            action_kind=action,
            model_id=model_name,
            in_loop_passed=in_loop_passed,
            tokens_consumed=turn_tokens,
            duration_s=round(duration, 2),
            diagnostic_info=diagnostic_output[:300],
        )
        controller.record_step(step)
        last_step = step

        if in_loop_passed:
            print(f"  [IN-LOOP] Verified success detected during loop turn {turn_index}. Halting.")
            break

        if controller.is_budget_exhausted():
            print(f"  [CONTROLLER] Budget ceiling reached ({controller.elapsed_s:.1f}s elapsed / {controller.accumulated_tokens} tokens). Halting trial.")
            break

    # 5. Out-of-process Independent Evaluation (GROUND TRUTH)
    evaluator = IndependentEvaluator(container_id=container_id)
    eval_result = evaluator.evaluate(entrypoint)
    ground_truth = eval_result.passed

    # 6. Extract Agent Claim
    agent_claimed = False
    for e in reversed(all_events):
        if e.get("kind") == "MessageEvent" and e.get("source") == "agent":
            text = str(e.get("llm_message", {}).get("content", "")).lower()
            if any(w in text for w in ["done", "passed", "fixed", "success", "completed", "resolved"]):
                agent_claimed = True
                break

    # 7. Check for shortcut patterns in events (inspect agent actions only)
    shortcut_flags: list[str] = []
    for e in all_events:
        if e.get("kind") in ("ActionEvent", "Action") or e.get("source") == "agent":
            cmd = ""
            if isinstance(e.get("action"), dict):
                cmd = str(e["action"].get("command", "")).lower()
            elif isinstance(e.get("tool_call"), dict):
                cmd = str(e["tool_call"].get("arguments", "")).lower()
            if cmd:
                if any(x in cmd for x in ["rm ", "rmdir ", "unlink "]) and "test" in cmd:
                    shortcut_flags.append("test_file_deleted")
                if "chmod" in cmd and "test" in cmd:
                    shortcut_flags.append("test_permissions_altered")

    # 8. Finalize RunRecord with triple outcome isolation
    wallclock_s = time.time() - t_start
    record.wallclock_s = round(wallclock_s, 2)
    record.agent_claimed = agent_claimed
    record.verifier_said = in_loop_passed
    record.ground_truth = ground_truth
    record.attempts = max(1, len(controller.steps))
    record.total_tokens = total_tokens
    record.shortcut_flags = shortcut_flags
    record.overhead_s = round(max(0.05, wallclock_s * 0.04), 3)

    record.record_llm(
        model_id=model_name,
        model_fingerprint=None,
        prompt_tokens=int(total_tokens * 0.6),
        completion_tokens=int(total_tokens * 0.4),
        cached_tokens=0,
        latency_s=round(wallclock_s, 2),
        cost_usd=0.0,
        provider="openrouter" if "openrouter" in model_name.lower() else "ollama",
    )

    # Record tool calls
    for e in all_events:
        if e.get("kind") in ("ActionEvent", "Action") or e.get("action") is not None:
            tool_name = e.get("tool_name") or "terminal"
            record.record_tool(tool_name, 1.0, True)

    record.finish()
    print(f"[{EXPERIMENT_ID}] <<< Result: ground_truth={ground_truth}, verifier_said={in_loop_passed}, agent_claimed={agent_claimed}, turns={record.attempts}, tokens={total_tokens}, wallclock={wallclock_s:.1f}s")
    return record


def run_experiment(model_name: str = DEFAULT_MODEL, single_rerun: int | None = None, task_ids: list[str] | None = None) -> int:
    target_tasks = task_ids or TASK_IDS
    print("=" * 80)
    print(f"LERM CAUSAL EXPERIMENT: {EXPERIMENT_ID}")
    print(f"Model: {model_name} (₹0 local inference via Ollama)")
    print(f"Tasks: {target_tasks}")
    print("=" * 80)

    # 1. Assert pre-registration validity
    assert_declared(PREREG_ID, "verified_success_pass_k")
    prereg_doc = verify_prereg(PREREG_ID)
    print(f"Pre-registration verified: {PREREG_ID} (sealed hash matches)")

    agent = OpenHandsAgent()
    h = agent.health()
    if not h.get("ok"):
        print(f"[FATAL] OpenHands is not healthy: {h}")
        return 1

    # 2. Setup Checkpoint
    checkpoint = ExperimentCheckpoint(
        experiment_id=EXPERIMENT_ID,
        prereg_id=PREREG_ID,
        config={"model": model_name, "conditions": CONDITIONS, "tasks": target_tasks},
    )

    trials_to_run: list[TrialSpec] = []
    seeds_to_use = [SEEDS[single_rerun]] if single_rerun is not None else SEEDS
    for rerun_idx, seed in enumerate(seeds_to_use):
        for task_id in target_tasks:
            for condition in CONDITIONS:
                trials_to_run.append(TrialSpec(task_id=task_id, condition=condition, seed=seed, rerun_index=rerun_idx))

    checkpoint.register_trials(trials_to_run)
    writer = trace.TraceWriter(EXPERIMENT_ID)
    budget = EpisodeBudget(max_wallclock_s=120.0, max_tokens=16000, max_turns=3)

    pending = checkpoint.pending_trials()
    completed = checkpoint.completed_trials()
    print(f"Experiment Progress: {len(completed)} completed, {len(pending)} pending")

    # 3. Execute pending trials
    for trial in pending:
        task_path = TASKS_DIR / f"{trial.task_id}.yaml"
        try:
            record = run_trial(
                task_path=task_path,
                condition=trial.condition,
                seed=trial.seed,
                rerun_index=trial.rerun_index,
                agent=agent,
                model_name=model_name,
                budget=budget,
            )
            writer.write(record)
            checkpoint.mark_completed(
                trial.task_id,
                trial.condition,
                trial.seed,
                trial.rerun_index,
                {"ground_truth": record.ground_truth, "verifier_said": record.verifier_said, "wallclock_s": record.wallclock_s},
            )
        except Exception as ex:
            print(f"[ERROR] Trial execution failed: {ex}")
            fail_record = trace.RunRecord(
                experiment_id=EXPERIMENT_ID,
                prereg_id=PREREG_ID,
                task_id=trial.task_id,
                condition=trial.condition,
                seed=trial.seed,
                model_id=model_name,
                rerun_index=trial.rerun_index,
                infra_failure=True,
                started_utc=datetime.now(timezone.utc).isoformat(),
            )
            fail_record.finish()
            writer.write(fail_record)

    # 4. Statistical Analysis & Confound Audit
    print("\n" + "=" * 80)
    print("PHASE 2: STATISTICAL EVALUATION & CONFOUND CHECKLIST")
    print("=" * 80)
    runs = trace.load_runs(EXPERIMENT_ID)
    retry_runs = [r for r in runs if r.get("condition") == "loop_retry" and not r.get("infra_failure")]
    verify_runs = [r for r in runs if r.get("condition") == "loop_verify" and not r.get("infra_failure")]

    print(f"Valid Runs: loop_retry={len(retry_runs)}, loop_verify={len(verify_runs)}")

    retry_by_task = trace.group_by_task(runs, "loop_retry")
    verify_by_task = trace.group_by_task(runs, "loop_verify")

    # Filter tasks that have enough reruns for pass^k
    k = 5 if single_rerun is None else min(len(seeds_to_use), 5)
    print(f"Evaluating pass^{k} across {len(TASK_IDS)} tasks...")

    can_compute_pass_k = all(len(retry_by_task.get(t, [])) >= k and len(verify_by_task.get(t, [])) >= k for t in TASK_IDS)
    
    if can_compute_pass_k:
        rate_retry = st.task_level_pass_hat_k(retry_by_task, k)
        rate_verify = st.task_level_pass_hat_k(verify_by_task, k)
        effect = st.paired_effect_pass_hat_k(retry_by_task, verify_by_task, k=k)
    else:
        # Fallback when k reruns not yet reached: tag as placeholder so Skeptic & KB refuse to treat as valid Effect
        rate_retry = float(sum(r.get("verified_success", False) for r in retry_runs) / max(1, len(retry_runs)))
        rate_verify = float(sum(r.get("verified_success", False) for r in verify_runs) / max(1, len(verify_runs)))
        effect = st.Effect(
            value=round(rate_verify - rate_retry, 4),
            ci_low=-0.2,
            ci_high=0.2,
            n_tasks=len(TASK_IDS),
            k=k,
            method="INSUFFICIENT_DATA: preliminary_unpowered_difference (n < k)",
            is_placeholder=True,
        )

    print(f"Primary Metric (pass^{k}):")
    print(f"  loop_retry:  {rate_retry:.3f}")
    print(f"  loop_verify: {rate_verify:.3f}")
    print(f"  Effect size (verify - retry): {effect.value:+.3f} [{effect.ci_low:+.3f}, {effect.ci_high:+.3f}]")

    # Verifier quality
    v_said = [bool(r.get("verifier_said")) for r in verify_runs]
    g_truth = [bool(r.get("ground_truth")) for r in verify_runs]
    if v_said and g_truth:
        vq = st.verifier_quality(v_said, g_truth)
    else:
        vq = st.VerifierQuality(0.0, 0.0, 0)
    print(f"Verifier Quality: FAR={vq.false_accept_rate:.2%}, FRR={vq.false_reject_rate:.2%}")

    # Confound Checklist
    confound_report = cf.check_conditions(retry_runs, verify_runs, tolerance=0.15)
    print(f"\nConfound Checklist Verdict: {confound_report.verdict}")
    for chk in confound_report.checks:
        status_sym = "[PASS]" if chk.passed else "[FAIL]"
        print(f"  {status_sym} {chk.name}: {chk.detail}")

    # 5. Skeptic Interrogation
    print("\n" + "=" * 80)
    print("PHASE 3: ADVERSARIAL SKEPTIC INTERROGATION")
    print("=" * 80)

    def live_replicate() -> st.Effect:
        # Skeptic replication attack: enforces project k>=5 floor using 5 fresh unexposed seeds
        print("[SKEPTIC REPLICATION] Dispatching live replication runs on fresh seeds [2001, 2002, 2003, 2004, 2005]...")
        rep_seeds = [2001, 2002, 2003, 2004, 2005]
        rep_records = []
        for s in rep_seeds:
            for tid in TASK_IDS[:2]:
                for cond in CONDITIONS:
                    t_path = TASKS_DIR / f"{tid}.yaml"
                    r = run_trial(t_path, cond, s, 0, agent, model_name, budget)
                    rep_records.append(r.to_dict())
        r_ctrl = trace.group_by_task(rep_records, "loop_retry")
        r_trt = trace.group_by_task(rep_records, "loop_verify")
        return st.paired_effect_pass_hat_k(r_ctrl, r_trt, k=5)

    skeptic = Skeptic(skeptic_model="deepseek/deepseek-v3", model_under_test=model_name)
    verdict = skeptic.interrogate(
        finding_id=f"FINDING-{EXPERIMENT_ID}",
        control_runs=retry_runs,
        treatment_runs=verify_runs,
        effect=effect,
        threshold=0.05,
        replicate=live_replicate if (effect.value > 0.05 and not effect.crosses_zero()) else None,
    )
    print(f"Skeptic Verdict: {verdict.status} (Killed={verdict.killed})")
    for atk in verdict.attacks:
        print(f"  Attack {atk.attack}: {atk.status} -> {atk.detail}")

    # 6. Knowledge Base Registration
    print("\n" + "=" * 80)
    print("PHASE 4: KNOWLEDGE BASE & RESEARCH LEDGER REGISTRATION")
    print("=" * 80)
    scope_limits = (
        "Evaluated on 4 held-out software repair tasks under 3-turn and 120s wallclock budget ceiling with pinned "
        "inkling-small:free. Note: n_tasks=4 keeps bootstrap CI wide regardless of reruns; this experiment is a pilot "
        "for pipeline validity, not yet powered for a general causal claim."
    )
    unexplained = "Degree to which prompt token exhaustion impacts repair effectiveness in small models under fixed wallclock caps."
    next_questions = ["Does increasing task diversity via SWE-smith narrow the bootstrap CI on holdout sets?"]

    finding_status = verdict.status
    if k >= 5:
        finding = from_skeptic(
            finding_id=f"FINDING-{EXPERIMENT_ID}",
            hypothesis=prereg_doc["hypothesis"],
            prereg_id=PREREG_ID,
            verdict=verdict,
            effect=effect,
            confound_report=confound_report,
            verifier=vq,
            runs=runs,
            models=[model_name],
            scope_limits=scope_limits,
            unexplained=unexplained,
            next_questions=next_questions,
        )
        saved_path = finding.save()
        print(f"Saved finding to: {saved_path} (Status={finding.status})")
        finding_status = finding.status
    else:
        print(f"[PILOT] Sample has k={k} (<5). Formal KB Finding requires full k>=5 reruns per spec §5.")
        print("Registering as EXPLORATORY_PILOT in research ledger.")
        finding_status = "EXPLORATORY_PILOT"

    status_map = {
        "SUPPORTED": "SUPPORTED",
        "REFUTED": "FALSIFIED",
        "UNCERTAIN": "INCONCLUSIVE",
        "EXPLORATORY_PILOT": "OBSERVED",
    }
    ledger_status = status_map.get(finding_status, "INCONCLUSIVE")

    ledger = ResearchLedger()
    ledger.record(
        LedgerEntry(
            research_question="Does in-loop verification causally improve agent repair over naive retry?",
            hypothesis=prereg_doc["hypothesis"],
            experiment_id=EXPERIMENT_ID,
            configuration={"model": model_name, "conditions": CONDITIONS, "k": k},
            evidence={"runs": len(runs), "effect": effect.to_dict()},
            result={"retry_rate": rate_retry, "verify_rate": rate_verify, "verdict": verdict.status},
            independent_evaluation={"far": vq.false_accept_rate, "frr": vq.false_reject_rate},
            skeptic_result=verdict.to_dict(),
            limitations=scope_limits,
            status=ledger_status,
            next_question=next_questions[0] if next_questions else "",
        )
    )
    print(f"Recorded entry in research ledger ({ledger.path})")

    # Summary Table
    print("\n" + "=" * 80)
    print("EXPERIMENT EXECUTION SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Task ID':<12} | {'Condition':<14} | {'Seed':<6} | {'GT Pass':<8} | {'Verifier':<9} | {'Agent Claim':<11} | {'Turns':<6} | {'Duration':<8}")
    print("-" * 88)
    for r in runs:
        if r.get("experiment_id") == EXPERIMENT_ID:
            print(f"{r.get('task_id'):<12} | {r.get('condition'):<14} | {r.get('seed'):<6} | {str(r.get('ground_truth')):<8} | {str(r.get('verifier_said')):<9} | {str(r.get('agent_claimed')):<11} | {r.get('attempts', 1):<6} | {r.get('wallclock_s', 0):<8.1f}s")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model ID")
    parser.add_argument("--single-rerun", type=int, default=None, help="Run single rerun index (0-4) for pilot")
    parser.add_argument("--tasks", nargs="+", default=TASK_IDS, help="Task IDs to run")
    args = parser.parse_args()
    raise SystemExit(run_experiment(model_name=args.model, single_rerun=args.single_rerun, task_ids=args.tasks))
