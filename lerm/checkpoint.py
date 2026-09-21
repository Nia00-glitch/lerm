"""Experiment checkpoint and resume manager.

Ensures live and long-running experiments can survive interruption without
duplicating completed trials or altering seeds/configurations.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.environ.get("LERM_STATE_DIR", "state"))
CHECKPOINT_DIR = STATE_DIR / "checkpoints"


@dataclass
class TrialSpec:
    task_id: str
    condition: str
    seed: int
    rerun_index: int
    completed: bool = False
    result: dict[str, Any] | None = None


@dataclass
class CheckpointState:
    experiment_id: str
    prereg_id: str
    created_ts: float
    updated_ts: float
    config: dict[str, Any]
    trials: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExperimentCheckpoint:
    def __init__(self, experiment_id: str, prereg_id: str, config: dict[str, Any], root: Path | str = CHECKPOINT_DIR) -> None:
        self.experiment_id = experiment_id
        self.prereg_id = prereg_id
        self.config = config
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / f"{experiment_id}.json"
        self.trials: list[TrialSpec] = []
        if self.path.exists():
            self._load()
        else:
            self._save()

    def _save(self) -> None:
        state = CheckpointState(
            experiment_id=self.experiment_id,
            prereg_id=self.prereg_id,
            created_ts=getattr(self, "created_ts", time.time()),
            updated_ts=time.time(),
            config=self.config,
            trials=[asdict(t) for t in self.trials],
        )
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2)
        tmp.replace(self.path)

    def _load(self) -> None:
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.created_ts = data["created_ts"]
        self.trials = [TrialSpec(**t) for t in data.get("trials", [])]

    def register_trials(self, trial_specs: list[TrialSpec]) -> None:
        existing_keys = {(t.task_id, t.condition, t.seed, t.rerun_index) for t in self.trials}
        added = False
        for spec in trial_specs:
            key = (spec.task_id, spec.condition, spec.seed, spec.rerun_index)
            if key not in existing_keys:
                self.trials.append(spec)
                existing_keys.add(key)
                added = True
        if added:
            self._save()

    def pending_trials(self) -> list[TrialSpec]:
        return [t for t in self.trials if not t.completed]

    def completed_trials(self) -> list[TrialSpec]:
        return [t for t in self.trials if t.completed]

    def mark_completed(self, task_id: str, condition: str, seed: int, rerun_index: int, result: dict[str, Any]) -> None:
        for t in self.trials:
            if (t.task_id == task_id and t.condition == condition and 
                t.seed == seed and t.rerun_index == rerun_index):
                t.completed = True
                t.result = result
                break
        self._save()
