# EXP-LOOP-003 Protocol: 16. Calibration Operating Characteristics Analysis

**Status**: FROZEN  
**Computation Script**: `calc_operating_characteristics.py`  
**Methodology**: Exact Binomial Enumeration across Sequential Stages ($N_1 = 10$, $N = 20$).

## 1. Operating Characteristics Comparison

Let $p$ be the true single-shot pass probability of a candidate task.

### A. Standard Rule: $N=20$, $0.30 \le \hat{p} \le 0.70$ ($6 \le X \le 14$)

| True $p$ | $P(\text{Admit})$ | $P(\text{Stage 1 Floor Rejection})$ | $P(\text{Stage 1 Ceiling Rejection})$ | $P(\text{Stage 2 Rejection})$ | Interpretation |
|---|---|---|---|---|---|
| **0.05** | 0.0003 | 0.9139 | 0.0000 | 0.0858 | Correctly rejected floor task (99.97%) |
| **0.10** | 0.0106 | 0.7361 | 0.0000 | 0.2533 | Correctly rejected floor task (98.94%) |
| **0.15** | 0.0636 | 0.5443 | 0.0000 | 0.3921 | Strong floor rejection (93.64%) |
| **0.20** | 0.1863 | 0.3758 | 0.0000 | 0.4379 | Moderate false admission risk (18.63%) |
| **0.25** | **0.3670** | 0.2440 | 0.0000 | 0.3889 | **Elevated false admission risk (36.70%)** |
| **0.30** | 0.5639 | 0.1493 | 0.0001 | 0.2866 | Boundary value: 56.39% admitted |
| **0.40** | 0.8556 | 0.0464 | 0.0017 | 0.0963 | Target calibration zone: high admission |
| **0.50** | **0.9457** | 0.0107 | 0.0107 | 0.0328 | Ideal calibration midpoint: 94.57% admitted |
| **0.60** | 0.8556 | 0.0017 | 0.0464 | 0.0963 | Target calibration zone: high admission |
| **0.70** | 0.5639 | 0.0001 | 0.1493 | 0.2866 | Boundary value: 56.39% admitted |
| **0.75** | **0.3670** | 0.0000 | 0.2440 | 0.3889 | **Elevated false admission risk (36.70%)** |
| **0.80** | 0.1863 | 0.0000 | 0.3758 | 0.4379 | Moderate false admission risk (18.63%) |
| **0.85** | 0.0636 | 0.0000 | 0.5443 | 0.3921 | Strong ceiling rejection (93.64%) |
| **0.90** | 0.0106 | 0.0000 | 0.7361 | 0.2533 | Correctly rejected ceiling task (98.94%) |
| **0.95** | 0.0003 | 0.0000 | 0.9139 | 0.0858 | Correctly rejected ceiling task (99.97%) |

---

### B. Guardband Rule: $N=20$, $0.35 \le \hat{p} \le 0.65$ ($7 \le X \le 13$)

| True $p$ | $P(\text{Admit})$ | $P(\text{Stage 1 Floor Rejection})$ | $P(\text{Stage 1 Ceiling Rejection})$ | $P(\text{Stage 2 Rejection})$ | Improvement vs Standard |
|---|---|---|---|---|---|
| **0.05** | 0.0000 | 0.9139 | 0.0000 | 0.0861 | Zero leakage |
| **0.10** | 0.0023 | 0.7361 | 0.0000 | 0.2616 | 78% reduction in false admission |
| **0.15** | 0.0214 | 0.5443 | 0.0000 | 0.4343 | 66% reduction in false admission |
| **0.20** | **0.0849** | 0.3758 | 0.0000 | 0.5393 | **54% reduction in false admission** |
| **0.25** | **0.2103** | 0.2440 | 0.0000 | 0.5457 | **43% reduction in false admission** |
| **0.30** | 0.3856 | 0.1493 | 0.0001 | 0.4650 | Conservative boundary enforcement |
| **0.40** | 0.7355 | 0.0464 | 0.0017 | 0.2165 | Strong admission in target zone |
| **0.50** | **0.8770** | 0.0107 | 0.0107 | 0.1015 | High power at target midpoint |
| **0.60** | 0.7355 | 0.0017 | 0.0464 | 0.2165 | Strong admission in target zone |
| **0.70** | 0.3856 | 0.0001 | 0.1493 | 0.4650 | Conservative boundary enforcement |
| **0.75** | **0.2103** | 0.0000 | 0.2440 | 0.5457 | **43% reduction in false admission** |
| **0.80** | **0.0849** | 0.0000 | 0.3758 | 0.5393 | **54% reduction in false admission** |
| **0.85** | 0.0214 | 0.0000 | 0.5443 | 0.4343 | 66% reduction in false admission |
| **0.90** | 0.0023 | 0.0000 | 0.7361 | 0.2616 | 78% reduction in false admission |
| **0.95** | 0.0000 | 0.0000 | 0.9139 | 0.0861 | Zero leakage |

## 2. Statistical Conclusion
The guardband rule $0.35 \le \hat{p} \le 0.65$ cuts boundary leakage at $p=0.20 / 0.80$ by more than half (down to 8.49%), while maintaining $87.7\%$ admission probability for perfectly balanced tasks ($p=0.50$). This rule is adopted as the frozen calibration standard.
