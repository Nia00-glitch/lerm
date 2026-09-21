import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from lerm.stats import plan_experiment, pass_hat_k, paired_effect_pass_hat_k

print("=================================================================")
print("=== GATE A13: POWER ANALYSIS AUDIT FOR PRIMARY METRIC ===")
print("=================================================================\n")

# Run plan_experiment for reference
for mde in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
    plan = plan_experiment(baseline_rate=0.50, mde=mde, k=5, power=0.80, alpha=0.05)
    print(f"plan_experiment(p0=0.50, MDE={mde:.2f}, k=5): required n_tasks = {plan.n_tasks}, runs/arm = {plan.runs_per_condition}")

print("\n--- SIMULATION OF PAIRED BOOTSTRAP POWER FOR pass^5 WITH n_reruns=10 ---")
# Simulate actual power of paired_effect_pass_hat_k
# Task true difficulty p_i ~ Beta(a, b) with mean 0.50
# In control: p_ctrl_i = p_i
# In treatment: p_treat_i = p_i + true_lift
# For each task, draw n_reruns=10 Bernoulli trials for ctrl, and 10 for treat.
# Compute paired_effect_pass_hat_k and check if CI excludes 0.

def simulate_paired_power(n_tasks, true_lift, k=5, n_reruns=10, n_sims=200):
    rng = np.random.default_rng(42)
    sig_count = 0
    for _ in range(n_sims):
        ctrl_dict = {}
        treat_dict = {}
        for t in range(n_tasks):
            # Task baseline difficulty centered at 0.50
            p_base = rng.beta(2, 2)
            p_ctrl = max(0.01, min(0.99, p_base))
            p_treat = max(0.01, min(0.99, p_base + true_lift))
            
            ctrl_dict[f"T{t}"] = [bool(rng.random() < p_ctrl) for _ in range(n_reruns)]
            treat_dict[f"T{t}"] = [bool(rng.random() < p_treat) for _ in range(n_reruns)]
            
        effect = paired_effect_pass_hat_k(ctrl_dict, treat_dict, k=k, n_boot=1000, alpha=0.05)
        if effect.ci_low > 0.0:
            sig_count += 1
    return sig_count / float(n_sims)

for n_t in [8, 15, 20, 30, 40]:
    for lift in [0.15, 0.20]:
        pwr = simulate_paired_power(n_tasks=n_t, true_lift=lift, k=5, n_reruns=10, n_sims=50)
        print(f"Tasks={n_t:2d}, True Lift={lift:.2f} -> Empirical Power = {pwr:.2f}")
