"""Statistical core for LERM.

Everything the machine is allowed to claim has to pass through here.
Design rules:
  - pass^k (all-k-succeed reliability), never bare pass@1 as a headline.
  - Effect sizes always carry a CI. A point estimate alone is not a result.
  - N and k come from power analysis, not from vibes.
  - Early stopping only via a pre-declared alpha-spending boundary.

Depends on numpy + scipy only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Sequence

import numpy as np
from scipy import stats as sps

RNG_DEFAULT_SEED = 20260916


# --------------------------------------------------------------------------
# pass^k
# --------------------------------------------------------------------------

def pass_hat_k(successes: Sequence[bool], k: int) -> float:
    """Unbiased estimator of the probability that k independent reruns ALL succeed.

    `successes` is the outcome of n >= k reruns of the SAME (task, condition).
    Uses the hypergeometric (combinatorial) estimator rather than (c/n)**k,
    which is biased upward at small n.
    """
    n = len(successes)
    if n < k:
        raise ValueError(f"need n>=k reruns, got n={n}, k={k}")
    c = int(sum(bool(s) for s in successes))
    if c < k:
        return 0.0
    # C(c,k) / C(n,k)
    return float(math.comb(c, k) / math.comb(n, k))


def pass_at_k(successes: Sequence[bool], k: int) -> float:
    """Unbiased pass@k (at least one of k succeeds) — Chen et al. estimator.

    Reported only as a secondary metric. The reliability gap
    pass@k - pass^k is usually where the engineering signal lives.
    """
    n = len(successes)
    c = int(sum(bool(s) for s in successes))
    if n - c < k:
        return 1.0
    return float(1.0 - math.comb(n - c, k) / math.comb(n, k))


def reliability_gap(successes: Sequence[bool], k: int) -> float:
    return pass_at_k(successes, k) - pass_hat_k(successes, k)


def task_level_pass_hat_k(runs_by_task: dict[str, Sequence[bool]], k: int) -> float:
    """Mean pass^k across tasks. This is the primary metric for a condition."""
    if not runs_by_task:
        raise ValueError("no tasks")
    return float(np.mean([pass_hat_k(v, k) for v in runs_by_task.values()]))


# --------------------------------------------------------------------------
# Effect size with CI (paired over tasks, bootstrap)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Effect:
    value: float
    ci_low: float
    ci_high: float
    n_tasks: int
    k: int
    method: str
    is_placeholder: bool = False

    def crosses_zero(self) -> bool:
        return self.ci_low <= 0.0 <= self.ci_high

    def to_dict(self) -> dict:
        return asdict(self)


def paired_effect_pass_hat_k(
    control: dict[str, Sequence[bool]],
    treatment: dict[str, Sequence[bool]],
    k: int,
    n_boot: int = 10_000,
    alpha: float = 0.05,
    seed: int = RNG_DEFAULT_SEED,
) -> Effect:
    """Bootstrap CI for (treatment - control) mean pass^k, paired by task.

    Resamples TASKS, not runs: tasks are the unit of generalisation. Bootstrapping
    runs instead of tasks is the standard way agent papers get CIs that are far
    too narrow.
    """
    tasks = sorted(set(control) & set(treatment))
    if not tasks:
        raise ValueError("control and treatment share no tasks")
    c = np.array([pass_hat_k(control[t], k) for t in tasks])
    x = np.array([pass_hat_k(treatment[t], k) for t in tasks])
    diff = x - c
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(tasks), size=(n_boot, len(tasks)))
    boots = diff[idx].mean(axis=1)
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return Effect(
        value=float(diff.mean()),
        ci_low=float(lo),
        ci_high=float(hi),
        n_tasks=len(tasks),
        k=k,
        method=f"paired task bootstrap, B={n_boot}, alpha={alpha}",
    )


def two_proportion_p(succ_a: int, n_a: int, succ_b: int, n_b: int) -> float:
    """Two-sided Fisher exact p. Exact beats chi-square at the N we actually run."""
    table = [[succ_a, n_a - succ_a], [succ_b, n_b - succ_b]]
    return float(sps.fisher_exact(table, alternative="two-sided")[1])


# --------------------------------------------------------------------------
# Power analysis — decides N and k BEFORE the experiment
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PowerPlan:
    n_tasks: int
    k_reruns: int
    runs_per_condition: int
    baseline_rate: float
    mde: float
    power: float
    alpha: float

    def to_dict(self) -> dict:
        return asdict(self)


def plan_experiment(
    baseline_rate: float,
    mde: float,
    k: int = 5,
    power: float = 0.80,
    alpha: float = 0.05,
    max_tasks: int = 400,
) -> PowerPlan:
    """Tasks needed per condition to detect `mde` absolute lift at `power`.

    Works on the pass^k scale: a baseline pass@1 of p implies a pass^k floor of
    roughly p**k, which is what we are actually powering on. This is why naive
    agent experiments are chronically underpowered — they size for pass@1.
    """
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be in (0,1)")
    if mde <= 0:
        raise ValueError("mde must be > 0")
    p0 = baseline_rate ** k
    p1 = min(0.999, p0 + mde)
    z_a = sps.norm.ppf(1 - alpha / 2)
    z_b = sps.norm.ppf(power)
    pbar = (p0 + p1) / 2
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    n = math.ceil(num / ((p1 - p0) ** 2))
    n = max(20, min(n, max_tasks))
    return PowerPlan(
        n_tasks=n,
        k_reruns=k,
        runs_per_condition=n * k,
        baseline_rate=baseline_rate,
        mde=mde,
        power=power,
        alpha=alpha,
    )


# --------------------------------------------------------------------------
# Sequential testing — the ONLY legal way to stop early
# --------------------------------------------------------------------------

def obrien_fleming_boundary(info_fraction: float, alpha: float = 0.05) -> float:
    """Two-sided O'Brien-Fleming z boundary at a given information fraction.

    Pre-declare the look schedule in the preregistration. Peeking without a
    boundary is how a 'result' gets manufactured out of noise.
    """
    t = min(max(info_fraction, 1e-6), 1.0)
    z_a = sps.norm.ppf(1 - alpha / 2)
    return float(z_a / math.sqrt(t))


def may_stop_early(z_stat: float, info_fraction: float, alpha: float = 0.05) -> bool:
    return abs(z_stat) >= obrien_fleming_boundary(info_fraction, alpha)


# --------------------------------------------------------------------------
# Verifier quality — a verifier with an unmeasured FAR is not a verifier
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class VerifierQuality:
    false_accept_rate: float
    false_reject_rate: float
    n: float

    def to_dict(self) -> dict:
        return asdict(self)


def verifier_quality(verifier_said: Sequence[bool], ground_truth: Sequence[bool]) -> VerifierQuality:
    v = np.array([bool(a) for a in verifier_said])
    g = np.array([bool(a) for a in ground_truth])
    if v.shape != g.shape or v.size == 0:
        raise ValueError("verifier_said and ground_truth must be same non-empty length")
    neg = (~g).sum()
    pos = g.sum()
    far = float((v & ~g).sum() / neg) if neg else float("nan")
    frr = float((~v & g).sum() / pos) if pos else float("nan")
    return VerifierQuality(false_accept_rate=far, false_reject_rate=frr, n=int(v.size))


# --------------------------------------------------------------------------
# Single-proportion calibration statistics — Gate R4
# --------------------------------------------------------------------------

def wilson_score_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score confidence interval for a single binomial proportion.

    Preferred over Wald (which severely under-covers near boundaries) and
    Clopper-Pearson (which is unnecessarily conservative for sizing calibration).
    """
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    if not (0 <= successes <= n):
        raise ValueError(f"successes must be in [0, n], got {successes} out of {n}")
    p_hat = successes / n
    z = float(sps.norm.ppf(1 - alpha / 2))
    denom = 1.0 + (z ** 2) / n
    center = (p_hat + (z ** 2) / (2 * n)) / denom
    half_width = (z * math.sqrt((p_hat * (1 - p_hat) / n) + ((z ** 2) / (4 * (n ** 2))))) / denom
    return (max(0.0, float(center - half_width)), min(1.0, float(center + half_width)))


def clopper_pearson_interval(successes: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact Clopper-Pearson confidence interval based on Beta quantiles."""
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    if not (0 <= successes <= n):
        raise ValueError(f"successes must be in [0, n], got {successes} out of {n}")
    lower = 0.0 if successes == 0 else float(sps.beta.ppf(alpha / 2, successes, n - successes + 1))
    upper = 1.0 if successes == n else float(sps.beta.ppf(1 - alpha / 2, successes + 1, n - successes))
    return (lower, upper)


def calibration_sample_size(
    target_margin: float = 0.15,
    alpha: float = 0.05,
    p_assumed: float = 0.50,
) -> int:
    """Minimum sample size N to achieve target confidence margin E at confidence 1-alpha."""
    if target_margin <= 0:
        raise ValueError("target_margin must be > 0")
    z = float(sps.norm.ppf(1 - alpha / 2))
    n = math.ceil((z ** 2 * p_assumed * (1 - p_assumed)) / (target_margin ** 2))
    return int(n)


def evaluate_calibration_admission(
    successes: int,
    n: int,
    target_low: float = 0.30,
    target_high: float = 0.70,
    alpha: float = 0.05,
) -> tuple[str, tuple[float, float]]:
    """Evaluates task admission using Wilson 95% score interval against [target_low, target_high].

    Returns: (decision, (ci_low, ci_high))
      - 'ADMIT': Point estimate in [target_low, target_high] and CI substantially overlaps target region
      - 'REJECT_TOO_EASY': Point estimate > target_high and lower CI >= 0.50
      - 'REJECT_TOO_HARD': Point estimate < target_low and upper CI <= 0.50
    """
    ci_low, ci_high = wilson_score_interval(successes, n, alpha=alpha)
    p_hat = successes / n
    if p_hat > target_high and ci_low >= 0.50:
        return "REJECT_TOO_EASY", (ci_low, ci_high)
    if p_hat < target_low and ci_high <= 0.50:
        return "REJECT_TOO_HARD", (ci_low, ci_high)
    if target_low <= p_hat <= target_high:
        return "ADMIT", (ci_low, ci_high)
    return "UNCERTAIN", (ci_low, ci_high)

