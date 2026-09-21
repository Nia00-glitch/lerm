import subprocess
import yaml

cid = "oh-agent-server-4HZ7pXNof2iZ3VlupptCwF"

for task_file in ["HOLDOUT-002.yaml", "HOLDOUT-003.yaml", "HOLDOUT-004.yaml"]:
    print(f"\n==================================================")
    print(f"VERIFYING TASK: {task_file}")
    print(f"==================================================")
    with open(f"holdout/tasks/{task_file}", "r", encoding="utf-8") as f:
        task = yaml.safe_load(f)
    
    # Materialize files
    for f in task["setup"]["files"]:
        p = f"/workspace/project/{f['path']}"
        parent = "/".join(p.split("/")[:-1])
        subprocess.run(["docker", "exec", cid, "mkdir", "-p", parent], check=True)
        subprocess.run(["docker", "exec", "-i", cid, "sh", "-c", f"cat > '{p}'"], input=f["content"].encode(), check=True)
    
    # Show ls -la inside container
    entrypoint = task["ground_truth_checker"]["entrypoint"]
    checker_script = entrypoint.split()[1] # e.g. scripts/verify_tenant_state.py
    print(f"\n[CONTAINER LS] Checking existence of {checker_script}:")
    ls_out = subprocess.run(["docker", "exec", "-w", "/workspace/project", cid, "ls", "-la", checker_script], capture_output=True, text=True)
    print(ls_out.stdout)
    
    # Run setup / solution steps if needed so checker can pass
    if "002" in task_file:
        subprocess.run(["docker", "exec", "-w", "/workspace/project", cid, "python3", "scripts/migrate_step1.py"], check=True)
    elif "003" in task_file:
        subprocess.run(["docker", "exec", "-w", "/workspace/project", cid, "python3", "scripts/seed_db.py"], check=True)
        subprocess.run(["docker", "exec", "-w", "/workspace/project", cid, "rm", "-f", "data/records.sqlite.lock"], check=True)

    print(f"[RUN CHECKER] Executing: {entrypoint}")
    check_out = subprocess.run(["docker", "exec", "-w", "/workspace/project", cid, "sh", "-c", entrypoint], capture_output=True, text=True)
    print("Exit code:", check_out.returncode)
    print("Stdout:", check_out.stdout.strip())
    print("Stderr:", check_out.stderr.strip())
