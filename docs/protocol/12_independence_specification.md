# EXP-LOOP-003 Protocol: 12. Task Independence Specification

**Status**: FROZEN  
**Principle**: Every task in the primary and calibration pools must represent an independent coding problem to prevent clustered variance.

## 1. Unit of Independence

The statistical unit of independence for EXP-LOOP-003 is defined at the **Target Function / Method Level**:
- No two candidate tasks in the pool may mutate the same function, method, or class block within a repository.
- No two tasks may share identical diff lines or overlapping patch chunks.

## 2. Near-Duplicate & Semantic Duplicate Detection

The `CandidatePool` manager enforces independence via three orthogonal checks:
1. **Exact Mutation ID Check**: Duplicate `mutation_id` rejected.
2. **Unified Diff Hash Check**: SHA-256 of patch content must be unique across the entire pool (rejects same mutation under distinct IDs).
3. **Configuration Check**: The tuple `(repository, commit, mutation_rule, seed)` must be unique across all candidates.

## 3. Cluster Analysis
If multiple candidate tasks originate from the same repository, they must target distinct modules or disparate classes. In primary causal analysis, standard errors will be clustered at the repository level if repository-level intraclass correlation $\rho > 0.05$.
