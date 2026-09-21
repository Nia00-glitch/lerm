# EXP-LOOP-003 Protocol: 08. Ground-Truth Protocol

**Status**: FROZEN  
**Principle**: Evaluator integrity and separation from agent feedback.

## 1. Ground-Truth Verification Chain

Every candidate task must pass the 8-step verification chain prior to pool admission:

```
[A] Known-Good Baseline Commit
        │
        ▼
[B] Run Baseline Evaluator ────────────────► MUST RETURN: PASS (Exit 0)
        │
        ▼
[C] Apply Single Declared Mutation
        │
        ▼
[D] Run Ground-Truth Evaluator ────────────► MUST RETURN: FAIL (Exit != 0)
        │
        ▼
[E] Apply Inverse Reference Repair
        │
        ▼
[F] Run Ground-Truth Evaluator ────────────► MUST RETURN: PASS (Exit 0)
        │
        ▼
[G] Reset to Mutated State
        │
        ▼
[H] Verify Content Hash ───────────────────► MUST EQUAL: MUTATED_HASH
```

## 2. Independence of Ground Truth
- The ground-truth test suite is executed in a read-only mounted container or isolated directory.
- The agent has no write access to test files.
- The evaluator output during candidate screening is piped directly to the experiment ledger and never exposed to the agent.
- If any step in the chain fails, the candidate is immediately marked `REJECTED` and quarantined.
