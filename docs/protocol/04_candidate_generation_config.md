# EXP-LOOP-003 Protocol: 04. Candidate-Generation Configuration

**Status**: FROZEN  
**Principle**: Bit-for-bit deterministic reproducibility of task pool generation.

## 1. Generator Parameters

```yaml
candidate_generator:
  framework: "swe-smith"
  commit: "9b74ac08118a85c39c356802f7961893af73e07f"
  mode: "procedural"
  language: "python"
  max_entities_sampled: 10
  max_bugs_per_entity: 1
  interleave: false
  timeout_per_repo_seconds: 120
```

## 2. Process Isolation & Determinism Requirement

As proven by the Phase C Adversarial Audit:
1. `swe-smith` procedural modifiers instantiate their own `random.Random(24)` instances at module import time.
2. In-process sequential runs without resetting modifier RNGs produce state drift across consecutive runs.
3. **Mandatory Execution Rule**: Every candidate-generation invocation MUST run in an isolated fresh Python subprocess OR explicitly invoke `reseed_all(seed)` across `MAP_EXT_TO_MODIFIERS` before candidate sampling.

## 3. Configuration Hash

The canonical configuration hash is the SHA-256 of the normalized JSON string of the generator settings:
`CONFIG_HASH = "8f03dc16a4e320f3e691ba73efcb0cf7925e04e963ecf6d9a9cf58a5c37eb61b"`
