"""Knowledge base + negative-results registry.

Two rules this module enforces in code rather than in prose:
  - `unexplained` is mandatory and may not be an empty string. If a finding has
    nothing unexplained, it was not examined hard enough.
  - REFUTED findings are stored with equal prominence and permanently block a
    silent re-run of the same hypothesis. That is what makes day 200 smarter
    than day 1.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

FINDINGS_DIR = Path("findings")
NEGATIVE_DIR = Path("negative_results")

STATUSES = {"SUPPORTED", "REFUTED", "UNCERTAIN"}
BANNED_WORDS = ("promising", "seems to", "looks like", "suggests that it may")


class SchemaViolation(ValueError):
    pass


def hypothesis_key(text: str) -> str:
    """Stable key for 'have we already settled this?' lookups."""
    norm = re.sub(r"[^a-z0-9 ]", "", text.lower())
    norm = " ".join(sorted(set(norm.split())))
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


@dataclass
class Finding:
    id: str
    hypothesis: str
    preregistration: str
    conditions: list[str]
    tasks: dict
    models: list[str]
    n_runs: int
    k_reruns: int
    primary_metric: str
    effect_size: dict                 # {value, ci_low, ci_high}
    false_accept_rate: float
    false_reject_rate: float
    cost: dict                        # {usd, gpu_hours, wallclock}
    confounds_checked: list[str]
    skeptic_attempts: list[dict]
    status: str
    scope_limits: str
    unexplained: str
    next_questions: list[str] = field(default_factory=list)
    causal_verdict: str = "CORRELATIONAL"
    replications: list[str] = field(default_factory=list)
    human_signoff: bool = False
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise SchemaViolation(f"status must be one of {sorted(STATUSES)}, got {self.status!r}")
        if not self.unexplained.strip():
            raise SchemaViolation(
                f"{self.id}: 'unexplained' is mandatory and must be non-empty. "
                "If nothing is unexplained, the analysis was not adversarial enough."
            )
        if not self.scope_limits.strip():
            raise SchemaViolation(f"{self.id}: 'scope_limits' is mandatory")
        for word in BANNED_WORDS:
            if word in self.hypothesis.lower() or word in self.scope_limits.lower():
                raise SchemaViolation(
                    f"{self.id}: hedging language {word!r} is not allowed — "
                    "outcomes are SUPPORTED / REFUTED / UNCERTAIN only"
                )
        for key in ("value", "ci_low", "ci_high"):
            if key not in self.effect_size:
                raise SchemaViolation(f"{self.id}: effect_size missing {key!r}")
        if self.effect_size.get("is_placeholder"):
            raise SchemaViolation(f"{self.id}: cannot create Finding from placeholder effect size (n < k)")
        if self.k_reruns < 5:
            raise SchemaViolation(f"{self.id}: k_reruns must be >=5")
        if self.status == "SUPPORTED" and self.causal_verdict != "CAUSAL_ELIGIBLE":
            raise SchemaViolation(
                f"{self.id}: cannot set status to 'SUPPORTED' when causal_verdict is {self.causal_verdict!r}. "
                "Confound checklist must be CAUSAL_ELIGIBLE to claim SUPPORTED; otherwise UNCERTAIN or REFUTED."
            )

    @property
    def key(self) -> str:
        return hypothesis_key(self.hypothesis)

    def is_principle_eligible(self) -> tuple[bool, str]:
        """A machine may PROPOSE a principle. It may not DECLARE one."""
        if self.status != "SUPPORTED":
            return False, "not SUPPORTED"
        fams = {m.split("/")[0].split("-")[0].lower() for m in self.models}
        if len(fams) < 2:
            return False, f"needs >=2 model families, has {sorted(fams)}"
        if len(self.replications) < 1:
            return False, "needs independent replication across >=2 task families"
        if self.causal_verdict != "CAUSAL_ELIGIBLE":
            return False, "confound checklist did not clear"
        if not self.human_signoff:
            return False, "awaiting human sign-off (machine may propose, not declare)"
        return True, "eligible"

    def save(self, root: Path | str | None = None) -> Path:
        base = Path(root) if root else (FINDINGS_DIR if self.status != "REFUTED" else NEGATIVE_DIR)
        base.mkdir(parents=True, exist_ok=True)
        p = base / f"{self.id}.yaml"
        doc = asdict(self) | {"hypothesis_key": self.key}
        p.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
        return p


def load_all(*roots: Path | str) -> list[dict]:
    out = []
    for root in (roots or (FINDINGS_DIR, NEGATIVE_DIR)):
        for p in sorted(Path(root).glob("*.yaml")):
            out.append(yaml.safe_load(p.read_text(encoding="utf-8")))
    return out


def already_settled(hypothesis: str, *roots: Path | str) -> dict | None:
    """Refuse to re-run an experiment the knowledge base has already settled.

    Returns the prior finding if one exists with status SUPPORTED or REFUTED.
    UNCERTAIN does not block — that is exactly what deserves more runs.
    """
    key = hypothesis_key(hypothesis)
    for doc in load_all(*roots):
        if doc.get("hypothesis_key") == key and doc.get("status") in {"SUPPORTED", "REFUTED"}:
            return doc
    return None


def from_skeptic(
    finding_id: str,
    hypothesis: str,
    prereg_id: str,
    verdict,
    effect,
    confound_report,
    verifier,
    runs: list[dict],
    models: list[str],
    scope_limits: str,
    unexplained: str,
    next_questions: list[str] | None = None,
) -> Finding:
    """Assemble a Finding from the actual artefacts. No hand-written numbers."""
    conditions = sorted({r["condition"] for r in runs})
    return Finding(
        id=finding_id,
        hypothesis=hypothesis,
        preregistration=f"preregistrations/{prereg_id}.yaml",
        conditions=conditions,
        tasks={
            "public": sorted({r["task_id"] for r in runs if not r.get("private")}),
            "private_holdout_n": len({r["task_id"] for r in runs if r.get("private")}),
        },
        models=models,
        n_runs=len(runs),
        k_reruns=effect.k,
        primary_metric="verified_success_pass_k",
        effect_size={
            "value": effect.value,
            "ci_low": effect.ci_low,
            "ci_high": effect.ci_high,
            "is_placeholder": getattr(effect, "is_placeholder", False),
        },
        false_accept_rate=verifier.false_accept_rate,
        false_reject_rate=verifier.false_reject_rate,
        cost={
            "usd": round(sum(r.get("cost_usd", 0.0) for r in runs), 4),
            "gpu_hours": 0.0,
            "wallclock": round(sum(r.get("wallclock_s", 0.0) for r in runs) / 3600, 3),
        },
        confounds_checked=[c.name for c in confound_report.checks],
        skeptic_attempts=[a.to_dict() for a in verdict.attacks],
        status=verdict.status,
        causal_verdict=confound_report.verdict,
        scope_limits=scope_limits,
        unexplained=unexplained,
        next_questions=next_questions or [],
    )
