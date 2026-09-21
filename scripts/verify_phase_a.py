import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

components = [
    ("historical firewall", "lerm/firewall.py"),
    ("repairability classifier", "lerm/repairability.py"),
    ("trace purity validator", "lerm/trace_purity.py"),
    ("calibration logic & stats", "lerm/stats.py"),
    ("preregistration machinery", "lerm/prereg.py"),
    ("confound checks", "lerm/confounds.py"),
    ("adversarial skeptic", "lerm/skeptic.py"),
    ("task schema", "holdout/tasks/_schema.yaml"),
    ("swe-smith repo", "swe-smith/pyproject.toml"),
    ("reference target repo", "mewwts__addict.75284f95/addict/addict.py"),
]

print("=== PHASE A: STATIC COMPONENT PRESENCE AUDIT ===")
all_present = True
for name, path in components:
    exists = os.path.exists(path)
    status = "EXISTS" if exists else "MISSING"
    if not exists:
        all_present = False
    print(f"[{status:7}] {name:28} : {path}")

print("\n=== PHASE A: RUNTIME TEST VERIFICATION ===")
tests = [
    ("Core Statistical & Prereg Suite", [sys.executable, "tests/test_core.py"]),
    (
        "Adversarial Skeptic Planted Suite",
        [sys.executable, "tests/test_skeptic_planted.py"],
    ),
    ("Historical Firewall Negative Test", [sys.executable, "tests/test_firewall.py"]),
    (
        "Independent Repairability Test",
        [sys.executable, "tests/test_repairability.py"],
    ),
    ("Task Schema Validation", [sys.executable, "scripts/validate_tasks.py"]),
]

test_results = []
for name, cmd in tests:
    res = subprocess.run(cmd, capture_output=True, text=True)
    passed = res.returncode == 0
    test_results.append((name, passed, res.stdout.strip(), res.stderr.strip()))
    status = "PASS" if passed else "FAIL"
    print(f"[{status:4}] {name}")
    if not passed:
        print(f"       STDERR: {res.stderr.strip()}")
        print(f"       STDOUT: {res.stdout.strip()}")

print(
    f"\nSummary: Components Present={all_present}, Tests Passed={all(t[1] for t in test_results)}"
)
