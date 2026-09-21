import math

def binom_pmf(n, k, p):
    return math.comb(n, k) * (p**k) * ((1-p)**(n-k))

def eval_calibration_rule(p, n1=10, n2=10, target_min=0.30, target_max=0.70):
    prob_admit = 0.0
    prob_stage1_floor_reject = 0.0
    prob_stage1_ceil_reject = 0.0
    prob_stage2_reject = 0.0
    
    for x1 in range(n1 + 1):
        p_x1 = binom_pmf(n1, x1, p)
        if x1 <= 1:
            prob_stage1_floor_reject += p_x1
        elif x1 >= 9:
            prob_stage1_ceil_reject += p_x1
        else: # continue
            for x2 in range(n2 + 1):
                p_x2 = binom_pmf(n2, x2, p)
                tot_x = x1 + x2
                p_hat = tot_x / (n1 + n2)
                if target_min <= p_hat <= target_max:
                    prob_admit += p_x1 * p_x2
                else:
                    prob_stage2_reject += p_x1 * p_x2
                    
    return {
        'p': p,
        'p_admit': prob_admit,
        'p_s1_floor': prob_stage1_floor_reject,
        'p_s1_ceil': prob_stage1_ceil_reject,
        'p_s2_reject': prob_stage2_reject,
        'p_total_reject': 1.0 - prob_admit
    }

print("=== CALIBRATION OPERATING CHARACTERISTICS (N=20 Sequential) ===")
header = f"{'p':>5} | {'P(Admit)':>10} | {'P(S1 Floor)':>12} | {'P(S1 Ceil)':>12} | {'P(S2 Rej)':>10}"
print(header)
print("-" * len(header))
for p_val in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
    res = eval_calibration_rule(p_val)
    print(f"{res['p']:5.2f} | {res['p_admit']:10.4f} | {res['p_s1_floor']:12.4f} | {res['p_s1_ceil']:12.4f} | {res['p_s2_reject']:10.4f}")

print("\n=== CALIBRATION OPERATING CHARACTERISTICS WITH GUARDBAND [0.35, 0.65] ===")
print(header)
print("-" * len(header))
for p_val in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
    res = eval_calibration_rule(p_val, target_min=0.35, target_max=0.65)
    print(f"{res['p']:5.2f} | {res['p_admit']:10.4f} | {res['p_s1_floor']:12.4f} | {res['p_s1_ceil']:12.4f} | {res['p_s2_reject']:10.4f}")
