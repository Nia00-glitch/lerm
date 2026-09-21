import hashlib
import os
import subprocess
import sys


def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


repo_dir = os.path.abspath("mewwts__addict.75284f95")
target_file = os.path.join(repo_dir, "addict", "addict.py")
test_file = os.path.join(repo_dir, "test_addict.py")

bugs_dir = os.path.abspath(
    "logs/bug_gen/mewwts__addict.75284f95/mewwts__addict.75284f95/addict/addict.py/update_d19e35c3"
)

candidates = [
    (
        "CANDIDATE-01",
        "func_pm_ctrl_invert_if",
        os.path.join(bugs_dir, "bug__func_pm_ctrl_invert_if__c1h8dde8.diff"),
    ),
    (
        "CANDIDATE-02",
        "func_pm_remove_assign",
        os.path.join(bugs_dir, "bug__func_pm_remove_assign__r6mc4pwn.diff"),
    ),
    (
        "CANDIDATE-03",
        "func_pm_remove_loop",
        os.path.join(bugs_dir, "bug__func_pm_remove_loop__uuuikumf.diff"),
    ),
]

print("=================================================================")
print("=== GATE A10: CANDIDATE GENERATION VALIDITY (3 CANDIDATES) ===")
print("=================================================================\n")


def run_tests():
    res = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-q"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return res.returncode, res.stdout.strip(), res.stderr.strip()


# Step 0: Ensure clean baseline
subprocess.run(["git", "checkout", "addict/addict.py"], cwd=repo_dir, check=True)
baseline_hash = get_sha256(target_file)
code, out, _ = run_tests()
print(
    f"KNOWN-GOOD BASELINE: Exit={code}, Tests={out.splitlines()[-1] if out else ''}, Hash={baseline_hash[:16]}..."
)
assert code == 0, "Baseline tests failed"

for cid, rule, diff_path in candidates:
    print(f"\n--- TESTING {cid}: {rule} ---")
    print(f"Diff path: {diff_path}")

    # Read diff and normalize path separators if needed
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_text = f.read()

    # Apply patch via git apply
    p_proc = subprocess.run(
        ["git", "apply", "--ignore-whitespace", diff_path],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if p_proc.returncode != 0:
        # Fallback to normalized patch if Windows backslashes in header
        norm_diff = diff_text.replace("addict\\addict.py", "addict/addict.py")
        p_proc = subprocess.run(
            ["git", "apply", "--ignore-whitespace", "-"],
            input=norm_diff,
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )

    broken_hash = get_sha256(target_file)
    print(f"1. Mutation applied. Broken Fixture Hash: {broken_hash}")

    # Run tests on broken fixture
    b_code, b_out, b_err = run_tests()
    last_line = b_out.splitlines()[-1] if b_out else ""
    print(f"2. Ground-truth Checker on Broken Fixture: Exit={b_code}")
    print(f"   Summary: {last_line}")
    assert b_code != 0, f"Expected broken fixture to fail tests, but exit={b_code}"

    # Reset / Apply reference fix
    subprocess.run(
        ["git", "checkout", "addict/addict.py"], cwd=repo_dir, check=True
    )
    reset_hash = get_sha256(target_file)
    print(f"3. Reference fix applied / Reset Hash: {reset_hash}")
    assert (
        reset_hash == baseline_hash
    ), f"Reset hash mismatch: {reset_hash} != {baseline_hash}"

    # Run tests on fixed fixture
    f_code, f_out, _ = run_tests()
    f_last_line = f_out.splitlines()[-1] if f_out else ""
    print(f"4. Ground-truth Checker on Fixed Fixture: Exit={f_code}")
    print(f"   Summary: {f_last_line}")
    assert f_code == 0, f"Expected fixed fixture to pass tests, but exit={f_code}"
    print(f"RESULT: {cid} PASSED VALIDATION CHAIN CLEANLY.")
