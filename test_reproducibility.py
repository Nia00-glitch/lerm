import os
import sys
import shutil
import stat
import types
import hashlib

sys.modules['resource'] = types.ModuleType('resource')
sys.path.insert(0, os.path.abspath('swe-smith'))
sys.path.insert(0, os.path.abspath('.'))

import swesmith.constants
from swesmith.bug_gen.procedural.generate import main

_orig_rmtree = shutil.rmtree
def _win_rmtree(path, *args, **kwargs):
    def on_err(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass
    return _orig_rmtree(path, onerror=on_err)
shutil.rmtree = _win_rmtree

def rm_rf(p):
    if os.path.exists(p):
        for root, dirs, files in os.walk(p):
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), stat.S_IWRITE)
                except Exception:
                    pass
        shutil.rmtree(p, ignore_errors=True)

def hash_dir(dir_path):
    h = hashlib.sha256()
    for root, dirs, files in sorted(os.walk(dir_path)):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, dir_path)
            h.update(rel.encode())
            h.update(open(p, 'rb').read())
    return h.hexdigest()

print("=================================================================")
print("=== PHASE C: GENERATION DETERMINISM & REPRODUCIBILITY TEST ===")
print("=================================================================\n")

repo_name = "mewwts__addict.75284f95"
seed = 42
base_out = os.path.join(swesmith.constants.LOG_DIR_BUG_GEN, repo_name)

# Run 1
rm_rf(base_out)
rm_rf("logs/run1")
print("Run 1: Generating bug with seed=42...")
main(repo_name, max_bugs=1, seed=seed, max_entities=5)
shutil.copytree(base_out, "logs/run1")
hash1 = hash_dir("logs/run1")
print(f"Run 1 Composite Hash: {hash1}")

# Run 2
rm_rf(base_out)
rm_rf("logs/run2")
print("\nRun 2: Generating bug with seed=42 from clean state...")
main(repo_name, max_bugs=1, seed=seed, max_entities=5)
shutil.copytree(base_out, "logs/run2")
hash2 = hash_dir("logs/run2")
print(f"Run 2 Composite Hash: {hash2}")

print("\n--- REPRODUCIBILITY VERIFICATION ---")
print(f"Run 1 Hash: {hash1}")
print(f"Run 2 Hash: {hash2}")
assert hash1 == hash2, f"Nondeterminism detected! {hash1} != {hash2}"
print("RESULT: 100% BIT-FOR-BIT REPRODUCIBLE ACROSS INDEPENDENT RUNS.")
