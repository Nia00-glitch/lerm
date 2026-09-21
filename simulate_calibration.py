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


test_ps = [0.00, 0.10, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90, 1.00]

print("=== EXACT BINOMIAL ENUMERATION OF ADMISSION RULE ===")
print(f"{'True p':>8} | {'Probability ADMIT':>18} | {'Probability REJECT':>18} | {'Stage-2 probability':>20}")
print("-" * 72)

for p in test_ps:
    # Stage 1: X1 ~ Bin(10, p)
    # Stage 1 continue if 2 <= X1 <= 8
    p_stage2 = sum(binom_pmf(x1, 10, p) for x1 in range(2, 9))

    # Total admission probability
    p_admit = 0.0
    for x1 in range(2, 9):
        p_x1 = binom_pmf(x1, 10, p)
        for x2 in range(0, 11):
            p_x2 = binom_pmf(x2, 10, p)
            x_tot = x1 + x2
            p_hat = x_tot / 20.0
            low, high = wilson_score_interval(x_tot, 20, alpha=0.05)
            # Rule: 0.30 <= p_hat <= 0.70 AND Wilson CI intersects [0.30, 0.70]
            intersects = not (high < 0.30 or low > 0.70)
            if 0.30 <= p_hat <= 0.70 and intersects:
                p_admit += p_x1 * p_x2
    p_reject = 1.0 - p_admit
    print(f"{p:8.2f} | {p_admit:18.4f} | {p_reject:18.4f} | {p_stage2:20.4f}")
