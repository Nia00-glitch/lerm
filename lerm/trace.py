"""L1 trace layer.

Every LLM call, tool call, token, second and dollar at the OpenHands<->OmniRoute
boundary lands here as append-only JSONL. JSONL is the source of truth; DuckDB
(or SQLite when DuckDB is absent) is a derived analytical view that can always be
rebuilt.

The single most important thing in this file is that `agent_claimed`,
`verifier_said` and `ground_truth` are three separate fields and nothing is
allowed to collapse them.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TRACE_DIR = Path(os.environ.get("LERM_TRACE_DIR", "traces"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LLMCall:
    ts: str
    model_id: str
    model_fingerprint: str | None
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    latency_s: float
    cost_usd: float
    provider: str | None = None
    error: str | None = None


@dataclass
class ToolCall:
    ts: str
    name: str
    latency_s: float
    ok: bool
    error: str | None = None


@dataclass
class RunRecord:
    """One (task, condition, seed) execution of the agent-under-test."""

    experiment_id: str
    prereg_id: str
    task_id: str
    condition: str
    seed: int
    model_id: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_index: int = 0
    rerun_index: int = 0
    model_fingerprint: str | None = None

    # --- the three outcome fields that must never be merged -----------------
    agent_claimed: bool | None = None      # what the agent said it did
    verifier_said: bool | None = None      # what the in-loop verifier said
    ground_truth: bool | None = None       # what the independent harness scored

    attempts: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    wallclock_s: float = 0.0
    overhead_s: float = 0.0                # time added by LERM layers, for the <10% budget
    human_intervention: bool = False
    infra_failure: bool = False            # infra died != agent failed
    shortcut_flags: list[str] = field(default_factory=list)
    llm_calls: list[LLMCall] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    started_utc: str = field(default_factory=_now)
    ended_utc: str | None = None

    # ------------------------------------------------------------------ api

    def record_llm(self, **kw: Any) -> None:
        call = LLMCall(ts=_now(), **kw)
        self.llm_calls.append(call)
        self.total_tokens += call.prompt_tokens + call.completion_tokens
        self.cost_usd += call.cost_usd
        if self.model_fingerprint is None:
            self.model_fingerprint = call.model_fingerprint

    def record_tool(self, name: str, latency_s: float, ok: bool, error: str | None = None) -> None:
        self.tool_calls.append(ToolCall(ts=_now(), name=name, latency_s=latency_s, ok=ok, error=error))

    def finish(self) -> "RunRecord":
        self.ended_utc = _now()
        return self

    def verified_success(self) -> bool:
        """Ground truth if we have it, else verifier. Never the agent's own claim."""
        if self.ground_truth is not None:
            return bool(self.ground_truth)
        if self.verifier_said is not None:
            return bool(self.verifier_said)
        raise ValueError(f"run {self.run_id} has neither ground_truth nor verifier_said")

    def overhead_ratio(self) -> float:
        return self.overhead_s / self.wallclock_s if self.wallclock_s else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verified_success"] = (
            self.ground_truth if self.ground_truth is not None else self.verifier_said
        )
        return d


class TraceWriter:
    """Thread- and process-safe append-only JSONL sink, one file per experiment."""

    def __init__(self, experiment_id: str, root: Path | str = TRACE_DIR) -> None:
        self.path = Path(root) / f"{experiment_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, record: RunRecord) -> None:
        line = json.dumps(record.to_dict(), separators=(",", ":"), default=str)
        with self._lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def read(self) -> Iterator[dict]:
        if not self.path.exists():
            return iter(())
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


def load_runs(experiment_id: str, root: Path | str = TRACE_DIR) -> list[dict]:
    return list(TraceWriter(experiment_id, root).read())


def group_by_task(runs: list[dict], condition: str) -> dict[str, list[bool]]:
    """-> {task_id: [verified_success, ...]} for one condition, infra failures dropped.

    Infra failures are excluded and counted separately: counting a crashed
    sandbox as an agent failure is how infrastructure noise becomes a 'finding'.
    """
    out: dict[str, list[bool]] = {}
    for r in runs:
        if r.get("condition") != condition or r.get("infra_failure"):
            continue
        vs = r.get("verified_success")
        if vs is None:
            continue
        out.setdefault(r["task_id"], []).append(bool(vs))
    return out


def infra_failure_rate(runs: list[dict]) -> float:
    return (sum(1 for r in runs if r.get("infra_failure")) / len(runs)) if runs else 0.0


def median_overhead_ratio(runs: list[dict]) -> float:
    ratios = [
        (r.get("overhead_s") or 0.0) / r["wallclock_s"]
        for r in runs
        if r.get("wallclock_s")
    ]
    if not ratios:
        return 0.0
    ratios.sort()
    mid = len(ratios) // 2
    return ratios[mid] if len(ratios) % 2 else (ratios[mid - 1] + ratios[mid]) / 2


# --------------------------------------------------------------------------
# Analytical store: DuckDB if available, SQLite otherwise. Both rebuildable.
# --------------------------------------------------------------------------

def build_store(experiment_ids: list[str], db_path: str = "store/lerm.duckdb",
                root: Path | str = TRACE_DIR) -> str:
    rows = []
    for eid in experiment_ids:
        rows.extend(load_runs(eid, root))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    flat = [
        {k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()}
        for r in rows
    ]
    try:
        import duckdb  # type: ignore

        con = duckdb.connect(db_path)
        import pandas as pd

        con.register("df", pd.DataFrame(flat))
        con.execute("CREATE OR REPLACE TABLE runs AS SELECT * FROM df")
        con.close()
        return f"duckdb:{db_path} ({len(flat)} runs)"
    except ImportError:
        import sqlite3

        sq = db_path.replace(".duckdb", ".sqlite")
        con = sqlite3.connect(sq)
        if flat:
            cols = sorted({k for r in flat for k in r})
            con.execute(f"DROP TABLE IF EXISTS runs")
            con.execute(f"CREATE TABLE runs ({','.join(f'\"{c}\"' for c in cols)})")
            con.executemany(
                f"INSERT INTO runs VALUES ({','.join('?' * len(cols))})",
                [[r.get(c) for c in cols] for r in flat],
            )
        con.commit()
        con.close()
        return f"sqlite:{sq} ({len(flat)} runs) [duckdb not installed]"
