# EXP-LOOP-003 Protocol: 06. Calibration Protocol

**Status**: FROZEN  
**Principle**: Independent difficulty calibration without treatment exposure or feedback.

## 1. Candidate Isolation Rules

Calibration tasks must satisfy the following strict firewall guarantees:
- `data_role = "calibration"`
- `historical_exposure = False`
- `primary_exp_loop_003_eligible = False`
- **Zero Loop Exposure**: Candidate is NEVER exposed to `loop_retry` or `loop_verify`.
- **Zero Turn-2 Actions**: Maximum of exactly 1 agent turn (single-shot attempt).
- **Zero Verifier Diagnostics**: The agent receives no test output, error traces, or verification feedback.

## 2. Calibration Stopping & Admission Rule

To avoid ceiling tasks (trivially solved in Turn 1) and floor tasks (impossible / unrepairable), tasks undergo a 2-stage sequential evaluation:

### Stage 1: Preliminary Screen ($N_1 = 10$)
- Run $N_1 = 10$ single-shot trials with temperature $T=0.7$ and pinned seeds.
- If successes $X_1 \le 1$: **REJECT (Floor Task)**. Stop trial.
- If successes $X_1 \ge 9$: **REJECT (Ceiling Task)**. Stop trial.
- If $2 \le X_1 \le 8$: **CONTINUE** to Stage 2.

### Stage 2: Full Precision Evaluation ($N = 20$ total)
- Run $N_2 = 10$ additional single-shot trials (total $N = 20$).
- Total successes $X = X_1 + X_2$.
- Sample proportion: $\hat{p} = X / 20$.
- **Admission Threshold (Guardband Rule)**:
  $$0.35 \le \hat{p} \le 0.65 \quad (7 \le X \le 13)$$
- Wilson score 95% confidence interval must intersect $[0.30, 0.70]$.

## 3. Post-Calibration Handling (Design C: Deterministic Fixed Pool)
- A fixed initial candidate pool of $K=30$ deterministically generated candidates is evaluated in preregistered sequence.
- All candidates satisfying the admission rule enter the primary pool.
- Rejected candidates are logged with their deterministic rejection category and NEVER re-tested.
- No adaptive re-generation or post-hoc threshold tuning is permitted.
