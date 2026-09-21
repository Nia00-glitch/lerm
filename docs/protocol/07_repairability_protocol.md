# EXP-LOOP-003 Protocol: 07. Independent Repairability Protocol

**Status**: FROZEN  
**Implementation**: `lerm/repairability.py`  
**Principle**: Repairability must be proven independently of model capability and treatment traces.

## 1. Circularity Prohibition

Under NO circumstances may repairability be determined by:
- Agent success under `loop_retry` or `loop_verify`
- Verifier diagnostic feedback
- Model self-reported success or explanations
- Multi-turn execution traces

## 2. Independent Ground-Truth Repair Mechanism

For every candidate task, repairability is established via an **Independent Reference Patch**:
1. The reference patch is the exact inverse diff restoring the known-good AST state from the baseline commit.
2. The reference patch is applied mechanically using `git apply`.
3. The ground-truth test suite is executed.
4. If and only if the reference patch restores an exit code of `0` with 100% of unit tests passing, the task is classified as `REPAIRABLE`.

## 3. Repairability Classification Taxonomy

| Category | Definition | Action |
|---|---|---|
| `REPAIRABLE` | Reference patch cleanly restores 100% test pass. Test failures provide deterministic assertion/stack traces. | Candidate remains eligible for calibration. |
| `UNREPAIRABLE` | Reference patch cannot be applied cleanly, or tests still fail after reference patch. | REJECT candidate. Reason: `reference_repair_failure`. |
| `INFRASTRUCTURE` | Task failure is caused by timeouts, OOM, missing system libraries, or container termination. | REJECT candidate. Reason: `infrastructure_failure`. |
| `AMBIGUOUS` | Test suite exhibits non-deterministic pass/fail behavior across repeated runs. | REJECT candidate. Reason: `ambiguous`. |
| `EVALUATOR_FAILURE` | Test code itself contains syntax errors or unhandled exceptions in test harness. | REJECT candidate. Reason: `evaluator_failure`. |
