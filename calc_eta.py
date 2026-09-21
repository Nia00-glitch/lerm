import json

with open('traces/EXP-LOOP-001.jsonl', 'r', encoding='utf-8') as f:
    trials = [json.loads(line) for line in f if line.strip()]

total = 40
done = len(trials)
remaining = total - done

times = [t.get('wallclock_s', 0) for t in trials]
avg_time = sum(times) / max(1, len(times))
est_remaining_sec = avg_time * remaining

print(f"Total Trials: {total}")
print(f"Completed: {done}/{total} ({done/total*100:.1f}%)")
print(f"Remaining: {remaining}")
print(f"Avg time per trial: {avg_time:.1f}s")
print(f"Estimated time remaining: {est_remaining_sec/60:.1f} minutes ({est_remaining_sec:.0f}s)")
print("\nLast 5 completed trials:")
for t in trials[-5:]:
    tid = t.get("task_id")
    cond = t.get("condition")
    seed = t.get("seed")
    gt = t.get("ground_truth")
    dur = t.get("wallclock_s")
    print(f"  {tid:<12} | {cond:<12} | seed={seed} | gt={str(gt):<5} | {dur:.1f}s")
