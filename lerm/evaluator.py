"""Independent Evaluator.

Executes ground-truth verification completely isolated from agent claims.
Runs the programmatic checker inside the container sandbox or test environment.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationResult:
    passed: bool
    status: str            # PASS | FAIL | UNKNOWN
    evidence: str
    exit_code: int
    duration_s: float
    command: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "status": self.status,
            "evidence": self.evidence,
            "exit_code": self.exit_code,
            "duration_s": self.duration_s,
            "command": self.command,
        }


class IndependentEvaluator:
    def __init__(self, container_id: str | None = None, workdir: str = "/workspace/project") -> None:
        self.container_id = container_id
        self.workdir = workdir

    def evaluate(self, entrypoint: str, timeout_s: int = 180) -> EvaluationResult:
        if not entrypoint or not entrypoint.strip():
            return EvaluationResult(
                passed=False,
                status="UNKNOWN",
                evidence="No entrypoint specified in ground_truth_checker",
                exit_code=127,
                duration_s=0.0,
                command="",
            )

        t0 = time.perf_counter()
        full_cmd = f"export PATH=$PATH:/home/openhands/.local/bin; export PYTHONPATH=.:$PYTHONPATH; (which pytest >/dev/null 2>&1 || python3 -m pip install -q pytest 2>/dev/null); {entrypoint}"
        if self.container_id:
            subprocess.run(["docker", "unpause", self.container_id], capture_output=True)
            cmd = ["docker", "exec", "-w", self.workdir, self.container_id, "sh", "-c", full_cmd]
        else:
            cmd = ["sh", "-c", full_cmd]

        try:
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            dt = time.perf_counter() - t0
            stdout = p.stdout.strip()
            stderr = p.stderr.strip()
            evidence = (stdout + ("\n" + stderr if stderr else "")).strip()
            passed = (p.returncode == 0)
            return EvaluationResult(
                passed=passed,
                status="PASS" if passed else "FAIL",
                evidence=evidence or f"Exit code {p.returncode}",
                exit_code=p.returncode,
                duration_s=dt,
                command=entrypoint,
            )
        except subprocess.TimeoutExpired:
            return EvaluationResult(
                passed=False,
                status="FAIL",
                evidence=f"Ground-truth evaluator timed out after {timeout_s}s",
                exit_code=124,
                duration_s=timeout_s,
                command=entrypoint,
            )
        except Exception as e:
            return EvaluationResult(
                passed=False,
                status="UNKNOWN",
                evidence=f"Ground-truth evaluator execution error: {e}",
                exit_code=1,
                duration_s=time.perf_counter() - t0,
                command=entrypoint,
            )
