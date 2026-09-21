# EXP-LOOP-003 Protocol: 03. Mutation Policy

**Status**: FROZEN  
**Principle**: Mutations must introduce precise semantic bugs in tested logic, avoiding trivial syntactic crashes, formatting changes, or environmental failures.

## 1. Allowed Mutation Operators

The following LibCST-based procedural operators from `swesmith.bug_gen.procedural.python` are permitted:

| Operator Name | Category | AST Target | Expected Failure Mechanism | Rationale |
|---|---|---|---|---|
| `func_pm_ctrl_invert_if` | Control Flow | `If / Else` | Inverted conditional branch leads to wrong logic path during execution. | Forces semantic reasoning about branch conditions. |
| `func_pm_ctrl_shuffle` | Control Flow | Function body statements | Reordering statements breaks sequential state dependencies. | Exercises state-order debugging. |
| `func_pm_remove_assign` | Variable State | Target assignment | Omission of variable update leaves state uninitialized or stale. | Tests variable scope and initialization analysis. |
| `func_pm_remove_cond` | Control Flow | Conditional checks | Eliminates conditional guard, executing unintended fallback logic. | High diagnostic signal in pytest assertions. |
| `func_pm_remove_loop` | Control Flow | `For / While` loop | Omits iteration over container elements; returns partial results. | Exercises loop logic analysis. |

## 2. Prohibited Mutation Operators

The following mutation classes are strictly forbidden and cause automatic candidate rejection:

| Prohibited Class | Rationale | Rejection Rule |
|---|---|---|
| **Formatting-only changes** | No semantic impact; tests remain passing. | Rejection reason: `mutation_no_effect` |
| **Comment-only changes** | No bytecode change; zero semantic effect. | Rejection reason: `mutation_no_effect` |
| **Dead-code / unreachable code** | Code path is not exercised by tests. | Rejection reason: `mutation_no_effect` |
| **Test-file modifications** | Alters test expectations rather than system under test. | Rejection reason: `other` (schema violation) |
| **Dependency / environment changes** | Affects package installation rather than repository code. | Rejection reason: `infrastructure_failure` |
| **Syntax-breaking non-code changes** | Generates unparseable files that fail at import time without exercising unit tests. | Rejection reason: `evaluator_failure` |
| **Network-dependent mutations** | Code that makes external API calls. | Rejection reason: `infrastructure_failure` |

## 3. Ambiguity & Noise Mitigation
- Every candidate mutation MUST target an implementation file (`*.py`) and must NOT touch any test files (`test_*.py`, `tests/*`).
- Target functions must have direct test coverage in the existing unit test suite.
