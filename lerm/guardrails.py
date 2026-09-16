"""§9 guardrails. Wire these at P2, not at P8.

An unattended loop holding an API key is a financial hazard, and a provider that
silently swaps a model behind a stable ID invalidates every comparison made
across the swap. Both are handled here.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

STATE = Path(os.environ.get("LERM_STATE_DIR", "state"))
KILL_FILE = Path(os.environ.get("LERM_KILL_FILE", "state/KILL"))


class BudgetExceeded(RuntimeError):
    pass


class KillSwitchEngaged(RuntimeError):
    pass


@dataclass
class Caps:
    usd_per_hour: float = 3.0
    usd_per_day: float = 40.0
    usd_per_week: float = 200.0

    def to_dict(self) -> dict:
        return asdict(self)


class SpendLedger:
    """Append-only spend ledger with hard stop. Checked before every dispatch."""

    def __init__(self, caps: Caps | None = None, root: Path | str = STATE) -> None:
        self.caps = caps or Caps()
        self.path = Path(root) / "spend.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, usd: float, experiment_id: str = "") -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.time(), "usd": float(usd),
                                 "experiment_id": experiment_id}) + "\n")

    def _spent_since(self, seconds: float) -> float:
        if not self.path.exists():
            return 0.0
        cutoff = time.time() - seconds
        total = 0.0
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec["ts"] >= cutoff:
                    total += rec["usd"]
        return total

    def snapshot(self) -> dict:
        return {
            "hour": round(self._spent_since(3600), 4),
            "day": round(self._spent_since(86400), 4),
            "week": round(self._spent_since(604800), 4),
            "caps": self.caps.to_dict(),
        }

    def assert_within_caps(self) -> None:
        s = self.snapshot()
        for window, cap in (("hour", self.caps.usd_per_hour),
                            ("day", self.caps.usd_per_day),
                            ("week", self.caps.usd_per_week)):
            if s[window] >= cap:
                raise BudgetExceeded(
                    f"spend cap hit: ${s[window]:.2f} in the last {window} "
                    f"(cap ${cap:.2f}). Hard stop."
                )


def check_kill_switch(path: Path | str = KILL_FILE) -> None:
    """Called every controller cycle. `touch state/KILL` stops the machine."""
    p = Path(path)
    if p.exists():
        raise KillSwitchEngaged(f"kill switch file present at {p}; halting")


def engage(path: Path | str = KILL_FILE, reason: str = "manual") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"{datetime.now(timezone.utc).isoformat()} {reason}\n", encoding="utf-8")
    return p


def release(path: Path | str = KILL_FILE) -> None:
    Path(path).unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Model drift canary
# --------------------------------------------------------------------------

@dataclass
class CanaryResult:
    model_id: str
    fingerprint: str | None
    digest: str
    drifted: bool
    detail: str


def canary_digest(responses: list[str]) -> str:
    import hashlib
    return hashlib.sha256("\x1f".join(responses).encode()).hexdigest()[:16]


def check_drift(model_id: str, responses: list[str], fingerprint: str | None = None,
                root: Path | str = STATE) -> CanaryResult:
    """Run a fixed canary task set daily at temperature 0 and compare digests.

    A changed digest does not prove the weights changed, but it does mean
    cross-day comparisons are no longer safe without a re-baseline.
    """
    path = Path(root) / "canary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = canary_digest(responses)
    book = json.loads(path.read_text()) if path.exists() else {}
    prev = book.get(model_id)
    drifted = bool(prev) and (prev["digest"] != digest or prev.get("fingerprint") != fingerprint)
    book[model_id] = {"digest": digest, "fingerprint": fingerprint,
                      "ts": datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(book, indent=2), encoding="utf-8")
    detail = (
        "first baseline recorded" if not prev
        else ("DRIFT: response digest or fingerprint changed since "
              f"{prev['ts']} — re-baseline before comparing across this boundary"
              if drifted else "stable")
    )
    return CanaryResult(model_id, fingerprint, digest, drifted, detail)
