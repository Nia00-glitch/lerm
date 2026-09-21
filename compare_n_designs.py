import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lerm.stats import wilson_score_interval


def binom_pmf(k, n, p):
    if p == 0.0:
        return 1.0 if k == 0 else 0.0
    if p == 1.0:
        return 1.0 if k == n else 0.0
    return math.comb(n, k) * (p**k) * ((1.0 - p) ** (n - k))


def evaluate_fixed_n(n, test_ps, target_low=0.30, target_high=0.70):
    print(f"\n=== EVALUATING FIXED N = {n} (0.30 <= p_hat <= 0.70) ===")
    print(f"{'True p':>8} | {'P(ADMIT)':>12} | {'P(REJECT)':>12}")
    print("-" * 36)
    for p in test_ps:
        p_admit = 0.0
        for x in range(n + 1):
            p_hat = x / float(n)
            if target_low <= p_hat <= target_high:
                p_admit += binom_pmf(x, n, p)
        print(f"{p:8.2f} | {p_admit:12.4f} | {(1.0 - p_admit):12.4f}")


test_ps = [0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90]
evaluate_fixed_n(30, test_ps)
evaluate_fixed_n(40, test_ps)
