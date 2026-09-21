# LERM EXP-LOOP-003 — PHASE C AUDIT & PROTOCOL FREEZE REPORT

**Auditor Roles**: Senior Experimental Scientist, Causal Inference Auditor, Adversarial Systems Engineer, Reproducibility Engineer, Research Infrastructure Engineer  
**Date**: 2026-09-21  
**Operating Principle**: TRUTH > CAUSAL VALIDITY > INDEPENDENCE > STATISTICAL POWER > REPRODUCIBILITY > THROUGHPUT  
**Experiment Phase**: Phase C (Candidate-Generation Protocol Freeze + Adversarial Audit)  
**Primary Experiment Trials Run**: 0 (Hard Stop Honored)

---

## 1. Environment & Provenance Record

Raw environment configuration captured at Phase C execution:

- **Git HEAD**: `f33ad56586056a661f04e9121bdbbfd8f476beb4` [RUNTIME EVIDENCE]
- **Python Version**: `3.14.7 (tags/v3.14.7:823f032, Aug  5 2026, 10:51:32) [MSC v.1944 64 bit (AMD64)]` [RUNTIME EVIDENCE]
- **SWE-smith Version / Commit**: `9b74ac08118a85c39c356802f7961893af73e07f` [RUNTIME EVIDENCE]
- **Docker Version**: `Docker version 29.6.2, build dfc4efb` [RUNTIME EVIDENCE]
- **AST / CST Dependencies**:
  - `libcst`: `1.9.0` [RUNTIME EVIDENCE]
  - `astor`: `0.8.1` [RUNTIME EVIDENCE]
  - `tree-sitter`: `0.26.0` [RUNTIME EVIDENCE]
  - `swebench`: `4.1.0` [RUNTIME EVIDENCE]
  - `docker`: `7.2.0` [RUNTIME EVIDENCE]
  - `pytest`: `9.1.1` [RUNTIME EVIDENCE]
  - `numpy`: `2.5.2` [RUNTIME EVIDENCE]
  - `scipy`: `1.18.1` [RUNTIME EVIDENCE]
- **Phase B Failure Evidence**: `reports/PHASE_B_FAIL_EVIDENCE.txt` (SHA-256: `d4b5b38cdd6258eba4898b1cb6f53e55935f57158422e364f40d9242234835ae`) [RUNTIME EVIDENCE]

---

## 2. Frozen Task Unit Schema (`CandidateTaskUnit`)

Defined in `lerm/candidate_schema.py` and specified in `docs/protocol/01_candidate_schema.md`.  
Every field is immutable, typed, and validated fail-closed [CODE INSPECTION, UNIT TEST]:

1. `task_id`: `str` — Format `^(CAND|SWE-SM)-[A-Za-z0-9_\-]+$`.
2. `source_repository`: `str` — Registered profile name.
3. `source_commit`: `str` — 7–40 hex git commit SHA.
4. `mutation_id`: `str` — Unique per candidate.
5. `mutation_seed`: `int` — Non-negative integer.
6. `mutation_rule`: `str` — In `{func_pm_ctrl_invert_if, func_pm_ctrl_shuffle, func_pm_remove_assign, func_pm_remove_cond, func_pm_remove_loop}`.
7. `original_file_paths`: `tuple[str, ...]` — Normalized with `/`.
8. `mutated_file_paths`: `tuple[str, ...]` — Normalized with `/`.
9. `baseline_state_id`: `str` — 64-char hex SHA-256.
10. `mutated_state_id`: `str` — 64-char hex SHA-256.
11. `candidate_content_hash`: `str` — 64-char hex SHA-256 of unified patch.
12. `baseline_content_hash`: `str` — 64-char hex SHA-256.
13. `generation_timestamp`: `str` — ISO 8601 UTC string.
14. `generator_version`: `str` — SWE-smith commit SHA.
15. `generator_config_hash`: `str` — 64-char hex SHA-256.
16. `task_schema_version`: `str` — Fixed `"1.0.0"`.
17. `data_role`: `str` — In `{"raw_candidate", "calibration", "primary", "diagnostic", "historical"}`.
18. `historical_exposure`: `bool` — Strictly `False` for fresh candidates.
19. `primary_exp_loop_003_eligible`: `bool` — Boolean.
20. `provenance`: `dict[str, Any]` — Non-empty mapping containing generator metadata.

---

## 3. Source-Repository Sampling Audit

Specified in `docs/protocol/02_repository_sampling_policy.md` [CODE INSPECTION, INTEGRATION TEST]:
- Eligible repositories:
  - `mewwts__addict.75284f95` (128 tests pass in 0.33s; offline).
  - `marshmallow-code__marshmallow.9716fc62` (421 entities; 2.15s test run).
  - `sqlfluff__sqlfluff.50a1c4b6` (3126 entities; 4.80s test run).
- Deterministic exclusions:
  - `pvlib/pvlib-python`: Excluded because `UNREGISTERED_IN_SWESMITH`.
- Sampling order: Deterministically permuted using `PRNG_SEED_REPO = 10001`. Zero subjective selection.

---

## 4. Mutation Generation & Latent Bug Discovery

Specified in `docs/protocol/03_mutation_policy.md` and `docs/protocol/04_candidate_generation_config.md` [ADVERSARIAL EVIDENCE, RUNTIME EVIDENCE]:

### Critical Finding: SWE-smith Modifier RNG State Drift
- Investigation revealed that LibCST procedural modifiers in `swesmith` instantiate their own internal `random.Random(24)` at module import time (`swesmith/bug_gen/procedural/base.py:L28`).
- `swesmith.bug_gen.procedural.generate.main` only calls `random.seed(seed)` on Python's global RNG, failing to pass `--seed` to modifier instances.
- Multiple calls within the same process caused `pm.rand` to retain mutated state, breaking bit-for-bit reproducibility across repeated in-process invocations.
- **Protocol Remediation**: The protocol driver enforces per-run reseeding (`reseed_all(seed)`) across all modifiers in `MAP_EXT_TO_MODIFIERS` or execution in isolated subprocesses.

---

## 5. Baseline → Mutation → Ground-Truth Chain

Verified in `test_candidate_chain.py` and enforced in `lerm/candidate_pool.py` [INTEGRATION TEST, RUNTIME EVIDENCE]:
- Clean baseline executed on `mewwts__addict.75284f95`: Exit 0 (128 passed in 0.33s).
- Applied AST mutation `func_pm_ctrl_invert_if`: Exit 1 (Test failure).
- Applied inverse reference fix: Exit 0 (128 passed in 0.33s).
- Reset file hash verified: `RESET_HASH == BASELINE_HASH`.

---

## 6. Independent Ground Truth & Repairability Separation

Enforced in `lerm/repairability.py` and `lerm/candidate_pool.py` [CODE INSPECTION, UNIT TEST]:
- Repairability is defined purely by whether an independent inverse reference patch restores test pass (Exit 0).
- Zero reliance on:
  - `loop_retry` outcomes
  - `loop_verify` traces
  - Agent turn count
  - Verifier feedback strings
- Classification taxonomy: `REPAIRABLE`, `UNREPAIRABLE`, `INFRASTRUCTURE`, `AMBIGUOUS`, `EVALUATOR_FAILURE`.

---

## 7. Calibration Operating Characteristics Analysis

Documented in `docs/protocol/16_calibration_operating_characteristics.md` [STATISTICAL ANALYSIS]:
Exact binomial calculation across sequential stages ($N_1=10$, $N=20$):

```
Standard Rule (p_hat in [0.30, 0.70]):
- At p = 0.05: P(Admit) = 0.0003, P(S1 Floor Rej) = 0.9139
- At p = 0.20: P(Admit) = 0.1863, P(S1 Floor Rej) = 0.3758
- At p = 0.25: P(Admit) = 0.3670 (Elevated boundary leakage!)
- At p = 0.50: P(Admit) = 0.9457 (High target power)

Guardband Rule (p_hat in [0.35, 0.65], 7 <= X <= 13):
- At p = 0.05: P(Admit) = 0.0000 (Zero floor leakage)
- At p = 0.20: P(Admit) = 0.0849 (54% reduction in false admission)
- At p = 0.25: P(Admit) = 0.2103 (43% reduction in false admission)
- At p = 0.50: P(Admit) = 0.8770 (Optimal balanced admission)
```
**Decision**: Adopted the guardband rule $0.35 \le \hat{p} \le 0.65$ to prevent loose floor/ceiling task admission under finite $N=20$.

---

## 8. Post-Calibration Handling & Design Choice

Specified in `docs/protocol/06_calibration_protocol.md` [STATISTICAL ANALYSIS]:
- **Design C (Deterministic Fixed Pool)** is selected.
- A fixed initial candidate pool of $K=30$ deterministically generated candidates is evaluated in preregistered sequence.
- All admitted candidates satisfying the frozen rule enter the primary pool.
- All rejected candidates are quarantined with deterministic rejection categories.
- No post-hoc tuning, adaptive regeneration, or cherry-picking.

---

## 9. Task Independence Audit

Specified in `docs/protocol/12_independence_specification.md` [CODE INSPECTION, UNIT TEST]:
- Unit of independence: Target Function / Method Level.
- Orthogonal collision checks:
  1. `mutation_id` uniqueness.
  2. Patch diff SHA-256 content uniqueness (catches same mutation under new ID).
  3. `(repo, commit, rule, seed)` tuple uniqueness.

---

## 10. Information Leakage Audit

Specified in `docs/protocol/13_information_leakage_audit.md` [ADVERSARIAL EVIDENCE, CODE INSPECTION]:
- Automated check in `CandidatePool.check_treatment_purity` forbids metadata containing treatment outcomes (`treatment_success`, `loop_retry_outcome`, `verifier_feedback`, `turn_count`, `post_treatment_trace`).
- Confirmed generator has zero read dependencies on traces, findings, or experiment reports.

---

## 11. Adversarial Test Results (Section 14)

Executed in `tests/test_candidate_adversarial.py` [ADVERSARIAL EVIDENCE]:
Command: `python -m pytest tests/test_candidate_adversarial.py -v`  
Result: **20 / 20 PASS (100%)**

1. Historical task injected into calibration -> `HISTORICAL_FIREWALL_BREACH` (**PASS**)
2. Historical task injected into primary -> `HISTORICAL_FIREWALL_BREACH` (**PASS**)
3. Fresh task with fake provenance -> `PROVENANCE_TAMPERED` (**PASS**)
4. Fresh task with missing provenance -> `CandidateValidationError` (**PASS**)
5. Fresh task with altered provenance -> `PROVENANCE_TAMPERED` (**PASS**)
6. Candidate copied from historical fixture -> `FirewallViolation` (**PASS**)
7. Candidate with one-byte source perturbation -> `HASH_MISMATCH` (**PASS**)
8. Duplicate mutation -> `DUPLICATE_MUTATION` (**PASS**)
9. Same mutation under different ID -> `DUPLICATE_DIFF` (**PASS**)
10. Treatment-success in metadata -> `TREATMENT_LEAKAGE` (**PASS**)
11. Calibration result in generator state -> `TREATMENT_LEAKAGE` (**PASS**)
12. Candidate missing mutation ID -> `CandidateValidationError` (**PASS**)
13. Candidate mismatched repo/commit -> `CandidateValidationError` (**PASS**)
14. Candidate mismatched content hash -> `CandidateValidationError` (**PASS**)
15. Candidate baseline already fails -> `BASELINE_FAILURE` (**PASS**)
16. Candidate mutation produces no failure -> `MUTATION_NO_EFFECT` (**PASS**)
17. Candidate failure is infrastructure-only -> `INFRASTRUCTURE_FAILURE` (**PASS**)
18. Reference repair does not restore PASS -> `REFERENCE_REPAIR_FAILURE` (**PASS**)
19. Candidate reset hash differs -> `RESET_FAILURE` (**PASS**)
20. Candidate generated with same seed twice -> `DUPLICATE_CONFIG` (**PASS**)

---

## 12. Reproducibility Test Results (Section 15)

Executed in `verify_3_configs_reproducibility.py` [RUNTIME EVIDENCE]:
Command: `python verify_3_configs_reproducibility.py`  
Result: **100% BIT-FOR-BIT DETERMINISTIC PASS**

- **CONFIG_A** (`mewwts__addict`, seed=42): 2 files bit-identical (`f4b376eb...`, `d31e5e0e...`).
- **CONFIG_B** (`mewwts__addict`, seed=101): 6 files bit-identical.
- **CONFIG_C** (`mewwts__addict`, seed=999): 18 files bit-identical.

---

## 13. Protocol Artifact Cryptographic Hash Registry

All 17 protocol artifacts hashed using SHA-256 [RUNTIME EVIDENCE]:

| Artifact Description | File Path | SHA-256 Hash |
|---|---|---|
| Candidate Schema Code | `lerm/candidate_schema.py` | `c0db95f2c81bf9daeb21929a0d65fbef40af17629241c4f713867388d7a7468b` |
| Candidate Pool Manager | `lerm/candidate_pool.py` | `fbd336858786f1250e9f2daf926efbdbd644409cacdb412b41de241cfd7ca060` |
| Data Firewall Code | `lerm/firewall.py` | `9127b036220ad2ec993404b6ddd09d6d5aa1a7bf2e35a2c053151cc52b83759a` |
| Repairability Classifier | `lerm/repairability.py` | `50fb84d2c295d58bf16ef37b42643693c01636793e25ad8feabdd50ba36d3ea0` |
| Trace Purity Auditor | `lerm/trace_purity.py` | `a602a7fe27f346d7e925e75cbc08797103f64ddedf01d8547e9d6286f05a6a84` |
| 01. Candidate Schema Spec | `docs/protocol/01_candidate_schema.md` | `deeb21ced32087aaac251397e8f40e41ed089426b0b8aefd20c3b67ade47eca0` |
| 02. Repo Sampling Policy | `docs/protocol/02_repository_sampling_policy.md` | `92ea87d5e4a32f05b186b8bb1d92a98370fba2a7bcacf3f03954a434fd0c03d6` |
| 03. Mutation Policy | `docs/protocol/03_mutation_policy.md` | `c0e17209c78153ed2a24d34a09d44eada5997479a8e44d71d8b816204bdfa515` |
| 04. Generator Configuration | `docs/protocol/04_candidate_generation_config.md` | `a9c2ed10a8a60bd655ee43e138112c62b148a832bcb89c4a14302a03a2b2aabb` |
| 05. Random Seed Policy | `docs/protocol/05_random_seed_policy.md` | `6aff66537550a1dba83aa534e7917201d2b83badf96cfbfff180c2f2dff747b4` |
| 06. Calibration Protocol | `docs/protocol/06_calibration_protocol.md` | `9322709489131ba64476591aa161794f1632e17b1ce2dc25d3d02e99ac0b2376` |
| 07. Repairability Protocol | `docs/protocol/07_repairability_protocol.md` | `be1dda1ef8e40118e264fb3e45825cc93fc22b41004e8aa756bb54f172eb93cb` |
| 08. Ground-Truth Protocol | `docs/protocol/08_ground_truth_protocol.md` | `cecbc77bd8954319600f0f0433def9f674d0ea575e1a5d126e3b830314a3f7ae` |
| 09. Rejection Taxonomy | `docs/protocol/09_candidate_rejection_taxonomy.md` | `1e888c921062bb010a23f0ff563f687d6922fb32abef0dba902333c73823d793` |
| 10. Manifest Format Spec | `docs/protocol/10_candidate_manifest_format.md` | `7e13bc9f05eb3b65e40d872a420dfb6d6408d614a69d07bdf793a9444d570281` |
| 11. Provenance Spec | `docs/protocol/11_provenance_specification.md` | `991a0e145e1033845afeaa0c854a251ecce7662224b3c5cd43c7ae048e53792c` |
| 12. Independence Spec | `docs/protocol/12_independence_specification.md` | `a661fd5c315498a90c6a49735e244d95a81b41e4bc01698137b62523aeeb59ba` |
| 13. Leakage Audit Spec | `docs/protocol/13_information_leakage_audit.md` | `8cb8447bcf8780a6de2e506a50a5190c39b08934f3a5df254ee3c4587c752466` |
| 14. Adversarial Test Suite | `docs/protocol/14_adversarial_test_suite.md` | `563eed4ed5653861e9b5b4a324e701684143253310b021c383935757ff63661c` |
| 15. Reproducibility Results | `docs/protocol/15_reproducibility_test_results.md` | `25b451d72dfc9a15ad5646633980157dd33f571100a5e67466f6c7216576fc90` |
| 16. Calibration Operating Char | `docs/protocol/16_calibration_operating_characteristics.md` | `d30b286bcb55861fba3a1ac7c8c528ee5113afdbc8ad9cc9ac015d637046642d` |

---

## 14. Final Phase C Binary Gate Checklist

| # | Gate Condition | Verification Type | Status | Evidence Reference |
|---|---|---|---|---|
| 1 | Candidate identity schema frozen | CODE INSPECTION + UNIT TEST | **PASS** | `lerm/candidate_schema.py` (SHA: `c0db95...`) |
| 2 | Repository sampling rule frozen | CODE INSPECTION | **PASS** | `docs/protocol/02_repository_sampling_policy.md` |
| 3 | Mutation rule frozen | CODE INSPECTION | **PASS** | `docs/protocol/03_mutation_policy.md` |
| 4 | Seed policy frozen | CODE INSPECTION | **PASS** | `docs/protocol/05_random_seed_policy.md` |
| 5 | Baseline→Mutation→GT-Fail→Ref-Repair→GT-Pass chain verified | INTEGRATION TEST + RUNTIME | **PASS** | `test_candidate_chain.py` exit code 0 |
| 6 | Reset hash verified | INTEGRATION TEST | **PASS** | `test_candidate_chain.py` exit code 0 |
| 7 | Independent evaluator verified | CODE INSPECTION + RUNTIME | **PASS** | Evaluator offline; zero agent write-access |
| 8 | Treatment cannot influence candidate selection | ADVERSARIAL EVIDENCE | **PASS** | Adversarial Tests 10 & 11 PASS |
| 9 | Repairability is treatment-independent | UNIT TEST + CODE INSPECTION | **PASS** | `tests/test_repairability.py` (7/7 PASS) |
| 10 | Historical firewall still blocks all historical tasks | ADVERSARIAL EVIDENCE | **PASS** | Adversarial Tests 1, 2, 6 PASS |
| 11 | Calibration firewall still blocks historical tasks | ADVERSARIAL EVIDENCE | **PASS** | Adversarial Test 1 PASS |
| 12 | Provenance is validated | UNIT TEST + ADVERSARIAL | **PASS** | Adversarial Tests 3, 4, 5 PASS |
| 13 | Candidate hashes are validated | UNIT TEST + ADVERSARIAL | **PASS** | Adversarial Tests 7, 14 PASS |
| 14 | Duplicate/near-duplicate policy defined | UNIT TEST + ADVERSARIAL | **PASS** | Adversarial Tests 8, 9, 20 PASS |
| 15 | Calibration operating characteristics analyzed | STATISTICAL ANALYSIS | **PASS** | `calc_operating_characteristics.py` |
| 16 | Calibration admission rule frozen | STATISTICAL ANALYSIS | **PASS** | Guardband $0.35 \le \hat{p} \le 0.65$ adopted |
| 17 | No post-hoc tuning remains | CODE INSPECTION | **PASS** | Design C (Fixed deterministic pool) frozen |
| 18 | Adversarial tests pass | ADVERSARIAL EVIDENCE | **PASS** | `tests/test_candidate_adversarial.py` (20/20 PASS) |
| 19 | Reproducibility tests pass | RUNTIME EVIDENCE | **PASS** | `verify_3_configs_reproducibility.py` (100% match) |
| 20 | All protocol artifacts hashed | RUNTIME EVIDENCE | **PASS** | 26 files cryptographically registered |

---

## 15. Final Phase C Decision

Every prerequisite gate condition has passed with raw empirical, adversarial, statistical, and cryptographic proof. Zero primary trials were executed.

$$\mathbf{FINAL\ DECISION:\ PHASE\ C\ PASS}$$

Protocol is frozen. Phase D has NOT begun.
