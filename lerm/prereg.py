"""Pre-registration. Written BEFORE execution, sealed by hash, git-committed.

Any analysis whose key is not in the sealed file is EXPLORATORY and can never be
promoted to a principle. This module enforces that mechanically: `seal()` refuses
to overwrite, and `verify()` fails loudly if the file changed after the runs began.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

PREREG_DIR = Path("preregistrations")


class PreregViolation(RuntimeError):
    """Raised when analysis strays outside the sealed plan."""


@dataclass
class Preregistration:
    id: str
    hypothesis: str                       # one falsifiable claim, not a topic
    conditions: list[str]
    primary_metric: str                   # e.g. verified_success_pass_k
    secondary_metrics: list[str] = field(default_factory=list)
    n_tasks: int = 0
    k_reruns: int = 5
    n_reruns: int = 10
    tasks_public: list[str] = field(default_factory=list)
    private_holdout_n: int = 0
    models: list[str] = field(default_factory=list)      # exact IDs, pinned
    decision_threshold: float = 0.0                      # absolute effect on primary metric
    alpha: float = 0.05
    power: float = 0.80
    stopping_rule: str = "obrien_fleming, looks at info_fraction 0.3/0.6/1.0"
    compute_matching: str = ""                           # how conditions are equalised
    predicted_failure_mode: str = ""
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        for name, val in (("hypothesis", self.hypothesis), ("primary_metric", self.primary_metric)):
            if not str(val).strip():
                raise ValueError(f"{name} must not be empty")
        if len(self.conditions) < 2:
            raise ValueError("need >=2 conditions to compare anything")
        if self.k_reruns < 5:
            raise ValueError("k_reruns must be >=5 — pass^k below k=5 is not informative here")
        if self.n_reruns < 2 * self.k_reruns:
            raise ValueError(
                f"n_reruns ({self.n_reruns}) must be >= 2 * k_reruns ({2 * self.k_reruns}) "
                f"to power pass^{self.k_reruns} estimation without collapsing to trivial outcomes"
            )

    # ---------------------------------------------------------------- sealing

    def payload(self) -> dict:
        d = asdict(self)
        d.pop("created_utc", None)
        return d

    def content_hash(self) -> str:
        blob = json.dumps(self.payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def path(self, root: Path | str = PREREG_DIR) -> Path:
        return Path(root) / f"{self.id}.yaml"

    def seal(self, root: Path | str = PREREG_DIR) -> Path:
        p = self.path(root)
        if p.exists():
            raise PreregViolation(
                f"{p} already exists. A preregistration is immutable. "
                "Allocate a new id instead of editing history."
            )
        p.parent.mkdir(parents=True, exist_ok=True)
        doc = asdict(self) | {"content_hash": self.content_hash()}
        p.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
        return p


def load(prereg_id: str, root: Path | str = PREREG_DIR) -> dict:
    p_direct = Path(prereg_id)
    if p_direct.exists() and p_direct.is_file():
        p = p_direct
    else:
        clean_id = Path(prereg_id).stem
        p = Path(root) / f"{clean_id}.yaml"
    if not p.exists():
        raise PreregViolation(f"no preregistration at {p} — refusing to run or analyse")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def verify(prereg_id: str, root: Path | str = PREREG_DIR) -> dict:
    """Re-hash the file and confirm nobody edited it after sealing."""
    doc = load(prereg_id, root)
    stored = doc.pop("content_hash", None)
    doc.pop("created_utc", None)
    recomputed = hashlib.sha256(
        json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if stored != recomputed:
        raise PreregViolation(
            f"{prereg_id}: content hash mismatch. The plan was edited after sealing. "
            "Every result derived from it is now EXPLORATORY."
        )
    return doc


def assert_declared(prereg_id: str, metric: str, root: Path | str = PREREG_DIR) -> None:
    """Gate every analysis call. Undeclared metric -> exploratory, hard stop."""
    doc = verify(prereg_id, root)
    declared = {doc.get("primary_metric")} | set(doc.get("secondary_metrics") or [])
    if metric not in declared:
        raise PreregViolation(
            f"metric '{metric}' is not in preregistration {prereg_id} "
            f"(declared: {sorted(x for x in declared if x)}). "
            "Label this EXPLORATORY; it cannot support a finding."
        )
