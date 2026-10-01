# LERM EXP-LOOP-003 — Baseline Dependency Provenance Audit

**Lead Roles**: Senior Experimental Scientist, Reproducibility Engineer, Dependency/Supply-Chain Auditor, Causal Inference Auditor, Adversarial Research Engineer  
**Date**: 2026-09-21  
**Governing Principle**: **TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT**  
**Gate Decision**: **`BLOCKED — BASELINE INELIGIBLE`**

---

## Executive Summary

This audit evaluates the baseline test failures observed in repositories `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` during the EXP-LOOP-003 Phase D preflight gate.

### Core Findings
1. **Marshmallow Missing Dependency**: `tests/conftest.py` fails on `import simplejson`. `simplejson` is declared in `pyproject.toml` under `[project.optional-dependencies].tests = ["pytest", "simplejson"]`. However, it has **no pinned version** (completely unpinned/floating), and the repository contains no lockfile or constraint file at commit `9716fc62`.
2. **Sqlfluff Missing Dependency**: Fails on `import sqlfluff` and subsequent `import tblib`. `sqlfluff` uses a `src/` layout and requires package installation (`python -m pip install -e .`) along with runtime dependencies (`tblib`, `diff-cover>=2.5.0`, `pathspec`, `regex`, etc.). All dependencies in `pyproject.toml` and `requirements_dev.txt` have floating/unpinned versions with no lockfile.
3. **Prohibition of Uncontrolled Installation**: Per hard rules G5 and G6, installing unpinned or floating versions from PyPI into the environment without an authoritative lockfile constitutes an uncontrolled environment mutation.
4. **Offline Isolation & Ineligibility**: Under Protocol 02 §2 (*“Deterministic Exclusion Rules: BASELINE_FAIL: Clean checkout fails any test”*), a clean checkout of `marshmallow` or `sqlfluff` fails tests offline in the execution plane.
5. **SWE-smith Deletion Defect**: In SWE-smith commit `9b74ac08118a85c39c356802f7961893af73e07f`, `swesmith/bug_gen/procedural/generate.py:L184` unconditionally calls `shutil.rmtree(repo)`. Running candidate generation deletes the local checkout directory, guaranteeing that subsequent offline baseline and ground-truth evaluators cannot access the repository unless a restoration mechanism is preregistered.

**Conclusion**: Repositories `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` trigger **`BASELINE_FAIL`** in the offline execution environment. Modifying the environment with floating packages or mutating SWE-smith is forbidden. Execution is **BLOCKED**.

---

## G1 — Frozen Policy Review

### 1. Source-Repository Sampling Policy (`docs/protocol/02_repository_sampling_policy.md`)
- **§1.2 (Testability & Reproducibility Requirements)**:
  > *“Clean, reproducible test suite executable offline via `pytest`.”*  
  > *“Baseline test execution time $< 10.0$ seconds for unit test suite.”*  
  > *“Zero flaky tests (10 consecutive baseline runs must yield 10 identical exit codes `0`).”*  
  > *“Zero external network dependencies during test execution (offline isolated execution).”*
- **§2 (Deterministic Exclusion Rules)**:
  > *“Repositories are excluded if:*  
  > *- `UNREGISTERED_IN_SWESMITH`: Repository is not defined in `swesmith/profiles/python.py` (e.g. `pvlib`).*  
  > *- `BASELINE_FAIL`: Clean checkout fails any test.*  
  > *- `TIMEOUT_EXCEEDED`: Test suite takes $> 10$ seconds.*  
  > *- `NETWORK_DEPENDENCY`: Tests require internet access.*  
  > *- `ENV_INCOMPATIBLE`: Requires non-standard system C libraries unavailable in the container runtime.”*

### 2. Ground-Truth Protocol (`docs/protocol/08_ground_truth_protocol.md`)
- **§1 (Ground-Truth Verification Chain)**:
  > *“[A] Known-Good Baseline Commit $\rightarrow$ [B] Run Baseline Evaluator $\rightarrow$ MUST RETURN: PASS (Exit 0)”*

### 3. Deviations Registry (`docs/DEVIATIONS.md`)
- No deviation exists authorizing runtime network package installations or unpinned dependency provisioning during Phase D.

---

## G2 — Audit of Marshmallow Dependency (`simplejson`)

### Repository State
- **Target**: `marshmallow-code__marshmallow.9716fc62`
- **Commit**: `9716fc629976c9d3ce30cd15d270d9ac235eb725`
- **Status**: Clean checkout.

### Provenance & Evidence from Repository Metadata

1. **`pyproject.toml` (Lines 24–44)**:
   ```toml
   requires-python = ">=3.9"
   dependencies = ["packaging>=17.0"]

   [project.optional-dependencies]
   docs = [
     "sphinx==8.1.3",
     "sphinx-issues==5.0.0",
     "alabaster==1.0.0",
     "sphinx-version-warning==1.1.2",
     "autodocsumm==0.2.14",
   ]
   tests = ["pytest", "simplejson"]
   dev = ["marshmallow[tests]", "tox", "pre-commit>=3.5,<5.0"]
   ```
2. **`tox.ini` (Lines 4–6)**:
   ```ini
   [testenv]
   extras = tests
   commands = pytest {posargs}
   ```
3. **`tests/conftest.py` & `tests/base.py` (Line 9)**:
   ```python
   import simplejson
   ```

### Findings
- `simplejson` is a **declared optional test dependency** (`[project.optional-dependencies].tests`).
- `pyproject.toml` declares `"simplejson"` **without any version constraint or pin**.
- The repository contains no `poetry.lock`, `Pipfile.lock`, `requirements.txt`, or constraint file at commit `9716fc62`.
- In an offline environment without `simplejson` pre-installed, a clean checkout fails immediately with:
  `ModuleNotFoundError: No module named 'simplejson'`.

---

## G3 — Audit of Sqlfluff Dependency (`sqlfluff` / `tblib`)

### Repository State
- **Target**: `sqlfluff__sqlfluff.50a1c4b6`
- **Commit**: `50a1c4b6ff171188b6b70b39afe82a707b4919ac`
- **Status**: Clean checkout.

### Provenance & Evidence from Repository Metadata

1. **Source Layout**:
   `sqlfluff` uses a `src/` directory layout (`src/sqlfluff/`). The test runner cannot import `sqlfluff` directly from root without `src` in `PYTHONPATH` or editable installation (`pip install -e .`).
2. **`src/sqlfluff/core/__init__.py` (Line 3)**:
   ```python
   import tblib.pickling_support
   ```
   Requires runtime third-party dependency `tblib`.
3. **`pyproject.toml` (Lines 68–97)**:
   ```toml
   dependencies = [
       "appdirs",
       "chardet",
       "click",
       "colorama>=0.3",
       "diff-cover>=2.5.0",
       "importlib_resources; python_version < '3.9'",
       "Jinja2",
       "pathspec",
       "pytest",
       "pyyaml>=5.1",
       "regex",
       "tblib",
       "toml; python_version < '3.11'",
       "tqdm",
   ]
   ```
4. **`requirements_dev.txt`**:
   Unpinned floating requirements (explicit header: `NOTE: Install with -U to keep all requirements up-to-date`).
5. **SWE-smith Profile Specification (`swe-smith/swesmith/profiles/python.py:L1142`)**:
   ```python
   install_cmds = ['python -m pip install -e .']
   test_cmd = 'source /opt/miniconda3/bin/activate; conda activate testbed; pytest --disable-warnings --color=no --tb=no --verbose'
   ```
   In SWE-smith's reference design, this is built into a dedicated container image with Conda. On the local host environment, these dependencies are uninstalled.

### Findings
- Running `pytest test/` fails with `ModuleNotFoundError: No module named 'sqlfluff'`.
- Running with `PYTHONPATH=src` fails with `ModuleNotFoundError: No module named 'tblib'`.
- All runtime and test dependencies are unpinned or use floating version ranges.

---

## G4 — Legitimate Provisioning Decision Table

| Repository | Missing Dependency | Declared by Repo? | Required for Tests? | Permitted to Provision? | Provenance Evidence |
|---|---|---|---|---|---|
| `mewwts__addict.75284f95` | None | N/A (Zero external deps) | Zero | **PASS (Ready)** | Self-contained single-module dictionary; 128 tests pass offline. |
| `marshmallow-code__marshmallow.9716fc62` | `simplejson` | Yes (`pyproject.toml:L42`) | Yes (`tests/base.py:9`) | **PROVISION_NOT_ALLOWED** | Completely unpinned in `pyproject.toml`; zero lockfile. Floating install from PyPI violates G5/G6. |
| `sqlfluff__sqlfluff.50a1c4b6` | `sqlfluff`, `tblib`, `diff-cover`, etc. | Yes (`pyproject.toml:L68-97`) | Yes (Core package) | **PROVISION_NOT_ALLOWED** | Open version ranges (`tblib`, `regex`, `diff-cover>=2.5.0`); floating install violates G5/G6. |

---

## G5 & G6 — Version Pinning & Supply-Chain Constraints

### Hard Rules Applied
- **Rule G5**: *“Do NOT execute: `pip install simplejson`, `pip install sqlfluff` unless G4 establishes that the installation is an authorized part of the reproducible environment. Do not install latest versions. Do not use floating versions. Do not use packages chosen merely because they make the tests pass.”*
- **Rule G6**: *“If an exact reproducible version cannot be established: STOP.”*

### Assessment
Neither `marshmallow` nor `sqlfluff` provides an exact frozen version hash or lockfile for testbed reproduction.
Arbitrarily running `pip install simplejson` or `pip install tblib` on the host machine would install whatever floating wheels are currently live on PyPI for Python 3.14. This would constitute an uncontrolled, post-hoc supply-chain intervention that invalidates causal reproducibility.

---

## G7 — Environment Baseline Hash

Captured prior to any modifications:
- **Python Version**: `Python 3.14.7`
- **Platform**: `Windows 11 Home Single Language (AMD64)`
- **Environment Status**: Global environment preserved. Zero ad-hoc packages installed.

---

## G8 & G9 — Offline 10-Run Baseline Evidence

### 1. `mewwts__addict.75284f95`
- **Command**: `1..10 | ForEach-Object { $out = (python -m pytest test_addict.py -q | Select-Object -Last 1); "$_ : $out" }`
- **Output**:
  ```text
  1 : 128 passed in 0.34s
  2 : 128 passed in 0.14s
  3 : 128 passed in 0.17s
  4 : 128 passed in 0.15s
  5 : 128 passed in 0.18s
  6 : 128 passed in 0.16s
  7 : 128 passed in 0.15s
  8 : 128 passed in 0.24s
  9 : 128 passed in 0.19s
  10 : 128 passed in 0.18s
  ```
- **Evaluation**: 10/10 runs exit code 0. Zero flakiness. Mean runtime 0.18s. Offline verified.
- **Status**: `PASS`

### 2. `marshmallow-code__marshmallow.9716fc62`
- **Command**: `python -m pytest tests/ -q`
- **Output**:
  ```text
  ImportError while loading conftest '...\tests\conftest.py'.
  E   ModuleNotFoundError: No module named 'simplejson'
  ```
- **Exit Code**: `1`
- **Evaluation**: Fails Step B of ground-truth chain immediately on clean checkout.
- **Status**: `FAIL (BASELINE_FAIL)`

### 3. `sqlfluff__sqlfluff.50a1c4b6`
- **Command**: `python -m pytest test/ -q`
- **Output**:
  ```text
  ImportError while loading conftest '...\test\conftest.py'.
  E   ModuleNotFoundError: No module named 'sqlfluff'
  ```
- **Exit Code**: `1`
- **Evaluation**: Fails Step B of ground-truth chain immediately on clean checkout.
- **Status**: `FAIL (BASELINE_FAIL)`

---

## G10 — SWE-smith Repository Deletion Risk Audit

### Code Inspection
In `swe-smith/swesmith/bug_gen/procedural/generate.py:L184`:
```python
total = process_with_timeout()

shutil.rmtree(repo)
print(f"Generated {total} bugs for {repo}.")
```

### Risk & Architectural Failure Mode
1. When `swesmith.bug_gen.procedural.generate.main(repo, ...)` completes candidate bug generation, it unconditionally executes `shutil.rmtree(repo)` on the local repository checkout directory.
2. In SWE-smith's standalone CLI workflow, it expects to clone fresh from a GitHub mirror upon every run.
3. In LERM's offline isolated experimental plane (Protocol 02 §1: *“Zero external network dependencies”*), once SWE-smith deletes the local clone directory, subsequent Phase D2 verification (`test_candidate_chain.py` Step B) finds no repository on disk and cannot re-clone without network access.
4. The frozen Phase D protocol design contains **no registered preservation/restoration mechanism** to handle this deletion.
5. Modifying `generate.py` in `swe-smith` without an authorized protocol deviation is prohibited.

---

## Final Gate Accounting & Decision

```text
=============================================================================
FINAL GATE STATUS: BLOCKED — BASELINE INELIGIBLE
=============================================================================
```

```text
Seed conflict: RESOLVED
Repository provisioning: PASS

mewwts baseline: PASS
marshmallow baseline: FAIL (ModuleNotFoundError: simplejson)
sqlfluff baseline: FAIL (ModuleNotFoundError: sqlfluff)

Dependency provenance:
marshmallow: FAIL (Unpinned floating test dependency; no lockfile)
sqlfluff: FAIL (Unpinned floating package dependencies; no lockfile)

Offline execution: PASS on mewwts; FAIL on marshmallow & sqlfluff
SWE-smith preservation mechanism: DEVIATION_REQUIRED (L184 rmtree deletes checkout)

D0 final rerun authorized: NO

Candidates generated: 0
Calibration trials: 0
Primary trials: 0
```

### Scientific Conclusion
In strict adherence to the governing principle:
$$\mathbf{TRUTH\ >\ CAUSAL\ VALIDITY\ >\ INDEPENDENCE\ >\ STATISTICAL\ POWER\ >\ REPRODUCIBILITY\ >\ THROUGHPUT}$$

We refuse to arbitrarily install floating third-party packages from PyPI to mask missing testbed dependencies, and we refuse to bypass the offline execution constraint of Protocol 02. Repositories `marshmallow-code__marshmallow.9716fc62` and `sqlfluff__sqlfluff.50a1c4b6` are deterministically disqualified under **`BASELINE_FAIL`**.

**Phase D1 candidate generation remains strictly BLOCKED.**
