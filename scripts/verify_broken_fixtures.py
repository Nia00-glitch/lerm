#!/usr/bin/env python3
"""Verify failure sensitivity and recovery of ground truth checkers.

For each holdout task (001, 002, 003, 004):
1. Materializes the unmodified setup.files into /workspace/project
2. Runs pre-fix checker -> asserts exit_code != 0 (FAIL on broken fixture)
3. Applies reference solution -> asserts exit_code == 0 (PASS on fixed code)
"""
import subprocess
import sys
import yaml
from pathlib import Path

CONTAINER = "oh-agent-server-AajqxBVbQlFXJphnMXMcS"
subprocess.run(["docker", "unpause", CONTAINER], capture_output=True)

def run_cmd(cmd, check=False):
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

def materialize(task_file):
    with open(f"holdout/tasks/{task_file}", "r", encoding="utf-8") as f:
        task = yaml.safe_load(f)
    # Clean project dir as root to remove any read-only locked files from previous runs
    run_cmd(["docker", "exec", "-u", "0", CONTAINER, "sh", "-c", "rm -rf /workspace/project/* /workspace/project/.* 2>/dev/null || true"])
    for f in task["setup"]["files"]:
        p = f"/workspace/project/{f['path']}"
        parent = "/".join(p.split("/")[:-1])
        run_cmd(["docker", "exec", "-u", "0", CONTAINER, "mkdir", "-p", parent])
        subprocess.run(["docker", "exec", "-u", "0", "-i", CONTAINER, "sh", "-c", f"cat > '{p}'"], input=f["content"].encode(), check=True)
    # Ensure openhands owns workspace except tests/
    run_cmd(["docker", "exec", "-u", "0", CONTAINER, "sh", "-c", "chown -R openhands:openhands /workspace/project"])
    return task

print("=" * 75)
print("GROUND TRUTH CHECKER AUDIT: PRE-FIX (FAIL) -> POST-FIX (PASS)")
print("=" * 75)

# --- HOLDOUT-001 ---
t001 = materialize("HOLDOUT-001.yaml")
e001 = t001["ground_truth_checker"]["entrypoint"]
res1_pre = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e001])
print(f"\n[HOLDOUT-001] Pre-fix exit code: {res1_pre.returncode}")
print(f"  Pre-fix stdout: {res1_pre.stdout.strip()[-150:]}")
assert res1_pre.returncode != 0, "HOLDOUT-001 must fail pre-fix!"

# Fix 001: remove DeprecationWarning from add()
fix001 = """
def add(a: int, b: int) -> int:
    return a + b

def safe_add(a: int, b: int) -> int:
    return a + b
"""
subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", "cat > /workspace/project/app/calc.py"], input=fix001.encode(), check=True)
res1_post = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e001])
print(f"  Post-fix exit code: {res1_post.returncode}")
print(f"  Post-fix stdout: {res1_post.stdout.strip()[-150:]}")
assert res1_post.returncode == 0, "HOLDOUT-001 must pass post-fix!"
print("  --> [VERIFIED] HOLDOUT-001 fails pre-fix, passes post-fix.")

# --- HOLDOUT-002 ---
t002 = materialize("HOLDOUT-002.yaml")
e002 = t002["ground_truth_checker"]["entrypoint"]
res2_pre = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e002])
print(f"\n[HOLDOUT-002] Pre-fix exit code: {res2_pre.returncode}")
print(f"  Pre-fix stderr: {res2_pre.stderr.strip()}")
assert res2_pre.returncode != 0, "HOLDOUT-002 must fail pre-fix!"

# Fix 002: run migrate_step1.py
run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "python3", "scripts/migrate_step1.py"], check=True)
res2_post = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e002])
print(f"  Post-fix exit code: {res2_post.returncode}")
print(f"  Post-fix stdout: {res2_post.stdout.strip()}")
assert res2_post.returncode == 0, "HOLDOUT-002 must pass post-fix!"
print("  --> [VERIFIED] HOLDOUT-002 fails pre-fix, passes post-fix.")

# --- HOLDOUT-003 ---
t003 = materialize("HOLDOUT-003.yaml")
e003 = t003["ground_truth_checker"]["entrypoint"]
# Run seed script to establish locked database
run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "python3", "scripts/seed_db.py"], check=True)
res3_pre = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e003])
print(f"\n[HOLDOUT-003] Pre-fix exit code: {res3_pre.returncode}")
print(f"  Pre-fix stderr: {res3_pre.stderr.strip()}")
assert res3_pre.returncode != 0, "HOLDOUT-003 must fail pre-fix!"

# Fix 003: remove lock file without deleting data
run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "rm", "-f", "data/records.sqlite.lock"], check=True)
res3_post = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e003])
print(f"  Post-fix exit code: {res3_post.returncode}")
print(f"  Post-fix stdout: {res3_post.stdout.strip()}")
assert res3_post.returncode == 0, "HOLDOUT-003 must pass post-fix!"
print("  --> [VERIFIED] HOLDOUT-003 fails pre-fix, passes post-fix.")

# --- HOLDOUT-004 ---
t004 = materialize("HOLDOUT-004.yaml")
e004 = t004["ground_truth_checker"]["entrypoint"]
res4_pre = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e004])
print(f"\n[HOLDOUT-004] Pre-fix exit code: {res4_pre.returncode}")
print(f"  Pre-fix stderr: {res4_pre.stderr.strip()}")
assert res4_pre.returncode != 0, "HOLDOUT-004 must fail pre-fix!"

# Fix 004: implement rotate_key
fix004 = """
active_keys = {"v1": "secret-key-alpha"}

def validate_token(token: str, key_version: str = "v1") -> bool:
    return token == f"valid_token_{active_keys.get(key_version)}"

def rotate_key(new_version: str, new_secret: str) -> None:
    active_keys[new_version] = new_secret
"""
subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", "cat > /workspace/project/api/server.py"], input=fix004.encode(), check=True)
res4_post = run_cmd(["docker", "exec", "-w", "/workspace/project", CONTAINER, "sh", "-c", e004])
print(f"  Post-fix exit code: {res4_post.returncode}")
print(f"  Post-fix stdout: {res4_post.stdout.strip()}")
assert res4_post.returncode == 0, "HOLDOUT-004 must pass post-fix!"
print("  --> [VERIFIED] HOLDOUT-004 fails pre-fix, passes post-fix.")

print("\n" + "=" * 75)
print("ALL 4 HOLDOUT TASKS FULLY VERIFIED: FAIL PRE-FIX, PASS POST-FIX.")
print("=" * 75)
