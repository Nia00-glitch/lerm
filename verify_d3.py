import subprocess

cid = "oh-agent-server-4HZ7pXNof2iZ3VlupptCwF"
# 1. Setup original unmodified fixture
calc_py = """import warnings

def add(a, b):
    warnings.warn("add() is deprecated, use safe_add() instead", DeprecationWarning, stacklevel=2)
    return a + b

def safe_add(a, b):
    return a + b
"""

test_calc_py = """import pytest
import warnings
from app.calc import add, safe_add

def test_safe_add():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        assert safe_add(2, 3) == 5
        assert len(rec) == 0, f"Expected 0 warnings, got {len(rec)}"

def test_negative():
    assert safe_add(-1, 1) == 0

def test_add_deprecation_removed():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        res = add(2, 3)
        assert res == 5
        deprecation_warnings = [w for w in rec if issubclass(w.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0, f"DeprecationWarning still raised: {[str(w.message) for w in deprecation_warnings]}"
"""

subprocess.run(["docker", "exec", cid, "mkdir", "-p", "/workspace/project/app", "/workspace/project/tests"])
subprocess.run(["docker", "exec", cid, "touch", "/workspace/project/app/__init__.py", "/workspace/project/tests/__init__.py"])
subprocess.run(["docker", "exec", "-i", cid, "sh", "-c", "cat > /workspace/project/app/calc.py"], input=calc_py.encode())
subprocess.run(["docker", "exec", "-i", cid, "sh", "-c", "cat > /workspace/project/tests/test_calc.py"], input=test_calc_py.encode())

print("=== RUNNING CHECKER ON ORIGINAL UNMODIFIED FIXTURE ===")
out_fail = subprocess.run(["docker", "exec", "-w", "/workspace/project", cid, "python3", "-m", "pytest", "tests/test_calc.py", "-q"], capture_output=True, text=True)
print("Exit Code:", out_fail.returncode)
print("Stdout:\n" + out_fail.stdout)
print("Stderr:\n" + out_fail.stderr)

# 2. Simulate fixed fixture
calc_fixed = """def add(a, b):
    return a + b

def safe_add(a, b):
    return a + b
"""
subprocess.run(["docker", "exec", "-i", cid, "sh", "-c", "cat > /workspace/project/app/calc.py"], input=calc_fixed.encode())

print("=== RUNNING CHECKER AFTER DEPRECATION WARNING REMOVED ===")
out_pass = subprocess.run(["docker", "exec", "-w", "/workspace/project", cid, "python3", "-m", "pytest", "tests/test_calc.py", "-q"], capture_output=True, text=True)
print("Exit Code:", out_pass.returncode)
print("Stdout:\n" + out_pass.stdout)
print("Stderr:\n" + out_pass.stderr)
