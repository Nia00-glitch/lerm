import json
import sys
import os
import numpy as np

trace_path = "traces/EXP-LOOP-002.jsonl"
records = [json.loads(line) for line in open(trace_path, "r", encoding="utf-8")]
valid = [r for r in records if not r.get("infra_failure", False)]

retry_records = [r for r in valid if r["condition"] == "loop_retry"]
verify_records = [r for r in valid if r["condition"] == "loop_verify"]

def stats(arr):
    a = np.array(arr)
    return {
        "mean": float(np.mean(a)),
        "median": float(np.median(a)),
        "std": float(np.std(a)),
        "p50": float(np.percentile(a, 50)),
        "p90": float(np.percentile(a, 90)),
    }

print("=================================================================")
print("=== GATE A14: EMPIRICAL COMPUTE EXPOSURE AUDIT ===")
print("=================================================================\n")

metrics = ["wallclock_s", "total_tokens", "attempts", "tool_calls_count"]
for r in retry_records + verify_records:
    r["tool_calls_count"] = len(r.get("tool_calls", []))

for m in metrics:
    s_ret = stats([r.get(m, 0) for r in retry_records])
    s_ver = stats([r.get(m, 0) for r in verify_records])
    print(f"--- Metric: {m} ---")
    print(f"  loop_retry  (n={len(retry_records)}): mean={s_ret['mean']:.2f}, median={s_ret['median']:.2f}, std={s_ret['std']:.2f}, p50={s_ret['p50']:.2f}, p90={s_ret['p90']:.2f}")
    print(f"  loop_verify (n={len(verify_records)}): mean={s_ver['mean']:.2f}, median={s_ver['median']:.2f}, std={s_ver['std']:.2f}, p50={s_ver['p50']:.2f}, p90={s_ver['p90']:.2f}")
    ratio = s_ver['mean'] / s_ret['mean'] if s_ret['mean'] > 0 else 0
    print(f"  Ratio (verify / retry): {ratio:.2f}x\n")

print("=================================================================")
print("=== GATE A15: VERIFIER COST DECOMPOSITION (ON ATTEMPTS > 1) ===")
print("=================================================================\n")

# Analyze trials where attempts > 1 (where repair/retry actually executed)
ret_multi = [r for r in retry_records if r.get("attempts", 1) > 1]
ver_multi = [r for r in verify_records if r.get("attempts", 1) > 1]

print(f"Trials with attempts > 1: loop_retry={len(ret_multi)}, loop_verify={len(ver_multi)}")

for m in ["wallclock_s", "total_tokens", "tool_calls_count"]:
    s_ret_m = stats([r.get(m, 0) for r in ret_multi]) if ret_multi else {}
    s_ver_m = stats([r.get(m, 0) for r in ver_multi]) if ver_multi else {}
    print(f"--- Metric on Multi-Attempt (Turns > 1): {m} ---")
    print(f"  loop_retry  (multi-attempt): mean={s_ret_m.get('mean', 0):.2f}, p50={s_ret_m.get('p50', 0):.2f}, p90={s_ret_m.get('p90', 0):.2f}")
    print(f"  loop_verify (multi-attempt): mean={s_ver_m.get('mean', 0):.2f}, p50={s_ver_m.get('p50', 0):.2f}, p90={s_ver_m.get('p90', 0):.2f}")
    if s_ret_m.get('mean', 0) > 0:
        print(f"  Multi-attempt Ratio: {s_ver_m['mean'] / s_ret_m['mean']:.2f}x")
