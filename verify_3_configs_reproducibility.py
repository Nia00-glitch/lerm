import os
import sys
import shutil
import stat
import types
import hashlib
import json
import glob
import random

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

def hash_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def inspect_run_artifacts(run_dir):
    artifacts = {}
    for root, dirs, files in sorted(os.walk(run_dir)):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, run_dir).replace('\\', '/')
            h = hash_file(p)
            artifacts[rel] = {
                'hash': h,
                'size': os.path.getsize(p)
            }
            if f.endswith('.json'):
                try:
                    artifacts[rel]['content'] = json.load(open(p, 'r', encoding='utf-8'))
                except Exception:
                    pass
    return artifacts

def run_config_twice(config_id, repo_name, seed, max_entities, max_bugs):
    print(f"\n=======================================================")
    print(f"=== TESTING CONFIGURATION {config_id}: {repo_name} (seed={seed}) ===")
    print(f"=======================================================")
    
    base_out = os.path.join(swesmith.constants.LOG_DIR_BUG_GEN, repo_name)
    run1_dir = f"logs/repro_test/{config_id}_run1"
    run2_dir = f"logs/repro_test/{config_id}_run2"
    
    from swesmith.bug_gen.procedural import MAP_EXT_TO_MODIFIERS
    def reseed_all(s):
        random.seed(s)
        for ext, pms in MAP_EXT_TO_MODIFIERS.items():
            for pm in pms:
                if hasattr(pm, 'rand'):
                    pm.rand.seed(s)
    
    rm_rf(base_out)
    rm_rf(run1_dir)
    print(f"[{config_id}] Launching Run 1...")
    reseed_all(seed)
    main(repo_name, max_bugs=max_bugs, seed=seed, max_entities=max_entities)
    shutil.copytree(base_out, run1_dir)
    art1 = inspect_run_artifacts(run1_dir)
    
    rm_rf(base_out)
    rm_rf(run2_dir)
    print(f"[{config_id}] Launching Run 2 from clean state...")
    reseed_all(seed)
    main(repo_name, max_bugs=max_bugs, seed=seed, max_entities=max_entities)
    shutil.copytree(base_out, run2_dir)
    art2 = inspect_run_artifacts(run2_dir)
    
    # Detailed comparison
    print(f"[{config_id}] Comparing artifacts between Run 1 and Run 2...")
    assert set(art1.keys()) == set(art2.keys()), f"File list mismatch: {set(art1.keys())} vs {set(art2.keys())}"
    
    for rel_path in sorted(art1.keys()):
        h1 = art1[rel_path]['hash']
        h2 = art2[rel_path]['hash']
        print(f"  File: {rel_path}")
        print(f"    Run 1 SHA-256: {h1}")
        print(f"    Run 2 SHA-256: {h2}")
        assert h1 == h2, f"Hash mismatch for {rel_path}: {h1} != {h2}"
    
    print(f"[{config_id}] PASS: Bit-for-bit identical output across independent runs.")
    return {
        'config_id': config_id,
        'repo': repo_name,
        'seed': seed,
        'files': list(art1.keys()),
        'hashes': {k: art1[k]['hash'] for k in art1}
    }

if __name__ == '__main__':
    configs = [
        ('CONFIG_A', 'mewwts__addict.75284f95', 42, 5, 1),
        ('CONFIG_B', 'mewwts__addict.75284f95', 101, 5, 1),
        ('CONFIG_C', 'mewwts__addict.75284f95', 999, 10, 1),
    ]
    
    results = []
    for cfg in configs:
        res = run_config_twice(*cfg)
        results.append(res)
        
    print("\n=======================================================")
    print("=== ALL 3 CONFIGURATIONS REPRODUCIBILITY SUMMARY ===")
    print("=======================================================")
    for r in results:
        print(f"{r['config_id']}: {r['repo']} (seed={r['seed']}) -> {len(r['files'])} files bit-identical")
    print("\nOVERALL REPRODUCIBILITY RESULT: 100% BIT-FOR-BIT DETERMINISTIC PASS")
