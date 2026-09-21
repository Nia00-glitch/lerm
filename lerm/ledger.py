"""Research ledger for LERM experiments.

Enforces structured scientific logging with controlled status values.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.environ.get("LERM_STATE_DIR", "state"))
LEDGER_DIR = STATE_DIR / "ledger"

VALID_STATUSES = {
    "OBSERVED",
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "FALSIFIED",
    "INCONCLUSIVE",
    "UNKNOWN",
}


@dataclass
class LedgerEntry:
    research_question: str
    hypothesis: str
    experiment_id: str
    configuration: dict[str, Any]
    evidence: dict[str, Any]
    result: dict[str, Any]
    independent_evaluation: dict[str, Any]
    skeptic_result: dict[str, Any]
    limitations: str
    status: str
    next_question: str
    regression_result: dict[str, Any] | None = None
    created_utc: str = ""

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{self.status}', must be one of {sorted(VALID_STATUSES)}")
        if not self.created_utc:
            self.created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.regression_result is None:
            d.pop("regression_result", None)
        return d


class ResearchLedger:
    def __init__(self, root: Path | str = LEDGER_DIR) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "research_ledger.jsonl"

    def record(self, entry: LedgerEntry) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def list_entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries
