# EXP-LOOP-003 Protocol: 05. Random Seed Policy

**Status**: FROZEN  
**Principle**: Preregistered, non-cherry-picked pseudo-random seed assignment.

## 1. Master Seed Hierarchy

All random operations in EXP-LOOP-003 derive hierarchically from a single preregistered master seed:
`MASTER_SEED = 20260921`

| Subsystem | Derived Seed Formula | Value | Purpose |
|---|---|---|---|
| **Repository Sampling** | `(MASTER_SEED + 101) % 100000` | `61022` | Shuffling repository order. |
| **Candidate Mutation Seed 1** | `(MASTER_SEED + 201) % 100000` | `61122` | Generating Candidate Batch A. |
| **Candidate Mutation Seed 2** | `(MASTER_SEED + 202) % 100000` | `61123` | Generating Candidate Batch B. |
| **Candidate Mutation Seed 3** | `(MASTER_SEED + 203) % 100000` | `61124` | Generating Candidate Batch C. |
| **Calibration Agent Seed Base**| `(MASTER_SEED + 500) % 100000` | `61421` | Base seed for Turn 1 single-shot agent sampling. |

## 2. Seed Constraints
- Seeds must never be changed after observing candidate difficulty or loop outcomes.
- Any change in seed constitutes a protocol deviation that must be preregistered in `docs/DEVIATIONS.md`.
- No seed search or "hunting for good tasks" is permitted under any circumstances.
