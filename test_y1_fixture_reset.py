import hashlib
import os
import subprocess
import yaml
from scripts.run_causal_experiment import materialize_task_files

container_id = "oh-agent-server-AajqxBVbQlFXJphnMXMcS"

# 1. Read canonical fixture content from YAML
with open("holdout/tasks/HOLDOUT-001.yaml", "r", encoding="utf-8") as f:
    task = yaml.safe_load(f)

files = task["setup"]["files"]
calc_fixture = next(f for f in files if f["path"] == "app/calc.py")
expected_canonical_sha = hashlib.sha256(calc_fixture["content"].encode("utf-8")).hexdigest()
print(f"CANONICAL BROKEN-FIXTURE HASH: {expected_canonical_sha}")

# --- TRIAL 1 ---
print("\n--- [TRIAL 1] Materializing task fixture into container ---")
materialize_task_files(container_id, files)

# Hash check immediately after materialization, before any agent action
res1 = subprocess.run(
    ["docker", "exec", container_id, "sha256sum", "/workspace/project/app/calc.py"],
    capture_output=True,
    text=True,
    check=True
)
hash_trial1 = res1.stdout.strip().split()[0]
print(f"TRIAL 1 Pre-Action On-Disk Hash:  {hash_trial1}")
assert hash_trial1 == expected_canonical_sha, f"Trial 1 mismatch: {hash_trial1} != {expected_canonical_sha}"

# Simulate Trial 1 Agent Action: agent fixes the deprecation warning
print("Simulating Trial 1 Agent Action: Agent fixes app/calc.py...")
fixed_content = "def add(a, b):\n    return a + b\n\ndef safe_add(a, b):\n    return a + b\n"
subprocess.run(
    ["docker", "exec", "-i", container_id, "sh", "-c", "cat > /workspace/project/app/calc.py"],
    input=fixed_content.encode("utf-8"),
    check=True
)
res_fixed = subprocess.run(
    ["docker", "exec", container_id, "sha256sum", "/workspace/project/app/calc.py"],
    capture_output=True,
    text=True,
    check=True
)
hash_fixed = res_fixed.stdout.strip().split()[0]
print(f"Post-Trial 1 Fixed File Hash:     {hash_fixed}")
assert hash_fixed != expected_canonical_sha, "Fix failed to alter hash"

# --- TRIAL 2 ---
print("\n--- [TRIAL 2] Materializing task fixture into container for next trial ---")
materialize_task_files(container_id, files)

# Hash check immediately after materialization for Trial 2
res2 = subprocess.run(
    ["docker", "exec", container_id, "sha256sum", "/workspace/project/app/calc.py"],
    capture_output=True,
    text=True,
    check=True
)
hash_trial2 = res2.stdout.strip().split()[0]
print(f"TRIAL 2 Pre-Action On-Disk Hash:  {hash_trial2}")
assert hash_trial2 == expected_canonical_sha, f"Trial 2 mismatch: {hash_trial2} != {expected_canonical_sha}"

print("\nEVIDENCE VERIFIED:")
print(f"Canonical Hash: {expected_canonical_sha}")
print(f"Trial 1 Hash:   {hash_trial1} (MATCHES CANONICAL: {hash_trial1 == expected_canonical_sha})")
print(f"Trial 2 Hash:   {hash_trial2} (MATCHES CANONICAL: {hash_trial2 == expected_canonical_sha})")
print(f"Trial 2 inherited Trial 1 fix? -> NO. Cleanly reset.")
