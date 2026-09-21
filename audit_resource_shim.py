import os
import sys

def audit_resource(dir_path, name):
    print(f"\n=======================================================")
    print(f"=== SEARCHING FOR 'resource' USAGE IN {name} ===")
    print(f"Path: {dir_path}")
    print(f"=======================================================")
    
    hits = []
    exact_api_hits = []
    for root, dirs, files in os.walk(dir_path):
        if any(skip in root for skip in [".git", "__pycache__", ".venv", "site-packages"]):
            if "swebench" not in root:
                continue
        for f in files:
            if f.endswith(".py"):
                full = os.path.join(root, f)
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as fp:
                        for idx, line in enumerate(fp, 1):
                            if "resource" in line:
                                hits.append((full, idx, line.strip()))
                            for api in ["getrlimit", "setrlimit", "RLIMIT", "import resource"]:
                                if api in line:
                                    exact_api_hits.append((full, idx, line.strip(), api))
                except Exception:
                    pass

    print(f"Total lines mentioning 'resource': {len(hits)}")
    print(f"Total lines using exact resource APIs (import/getrlimit/setrlimit/RLIMIT): {len(exact_api_hits)}")
    print("\n--- EXACT API HITS ---")
    for full, line_no, content, api in exact_api_hits:
        rel = os.path.relpath(full, os.path.dirname(dir_path))
        print(f"[{api}] {rel}:{line_no} -> {content}")

audit_resource("swe-smith", "SWE-smith Repo")

# Find swebench package directory
import swebench
audit_resource(os.path.dirname(swebench.__file__), "Installed swebench Package")
