# EXP-LOOP-003 Protocol: 13. Information Leakage Audit

**Status**: FROZEN  
**Principle**: Causal air-gap between generator, calibration, treatment, and evaluator.

## 1. Audit Scope & Pathways

The codebase was audited across all pathways by which treatment outcomes, verifier diagnostics, or calibration success could influence future candidate selection:

| Pathway Audited | Potential Leak Mechanism | Enforcement / Defense | Verification Result |
|---|---|---|---|
| **Filenames & Paths** | Embedding pass/fail status in candidate filenames | Candidate naming is strictly `CAND-XXX` or `SWE-SM-XXX` based on deterministic counter. | **PASSED (Audited)** |
| **Candidate Metadata**| Injecting treatment success into metadata | `CandidatePool.check_treatment_purity` scans for forbidden keys (`treatment_success`, etc.). | **PASSED (Adversarial Test 10)** |
| **Generator State** | Generator reading calibration outcomes to filter tasks | Generator operates strictly offline with frozen PRNG seeds. | **PASSED (Adversarial Test 11)** |
| **Cached Fixtures** | Reusing mutated fixtures from earlier runs | Fixtures are materialized per trial into ephemeral container mount. | **PASSED (Verified Gate Y1)** |
| **Historical Holdouts**| Ingesting EXP-LOOP-002 holdouts | `lerm/firewall.py` checks both task ID and fixture SHA-256 against immutable registry. | **PASSED (Adversarial Tests 1, 2, 6)** |
| **Verifier Traces** | Post-treatment logs used to define repairability | `lerm/repairability.py` uses only independent inverse patches; never inspects loop logs. | **PASSED (Audited)** |

## 2. Invariant Guarantee
The candidate generator has zero read dependencies on `traces/`, `findings/`, `reports/`, or treatment logs.
