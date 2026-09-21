# EXP-LOOP-003 Protocol: 15. Reproducibility Test Results

**Status**: FROZEN  
**Execution Script**: `verify_3_configs_reproducibility.py`  
**Result**: 100% BIT-FOR-BIT REPRODUCIBLE ACROSS INDEPENDENT RUNS.

## 1. Test Configurations

Three distinct configurations were executed twice from clean filesystem states:
1. **CONFIG_A**: `mewwts__addict.75284f95`, `seed=42`, `max_entities=5`, `max_bugs=1`
2. **CONFIG_B**: `mewwts__addict.75284f95`, `seed=101`, `max_entities=5`, `max_bugs=1`
3. **CONFIG_C**: `mewwts__addict.75284f95`, `seed=999`, `max_entities=10`, `max_bugs=1`

## 2. Comparison Summary

| Config ID | Repository | Seed | Entities | Bugs Generated | Total Files | Run 1 == Run 2 Status |
|---|---|---|---|---|---|---|
| **CONFIG_A** | `mewwts__addict.75284f95` | `42` | 5 | 1 | 2 | **100% Bit-Identical** |
| **CONFIG_B** | `mewwts__addict.75284f95` | `101` | 5 | 3 | 6 | **100% Bit-Identical** |
| **CONFIG_C** | `mewwts__addict.75284f95` | `999` | 10 | 9 | 18 | **100% Bit-Identical** |

## 3. Sample Cryptographic Artifact Hashes

### CONFIG_A
- Diff: `bug__func_pm_remove_cond__ty8un4e6.diff`
  - Run 1 SHA-256: `f4b376ebfd87bbbfa8ee67dfe6f835d1190a01dfec90961166d1d92836419900`
  - Run 2 SHA-256: `f4b376ebfd87bbbfa8ee67dfe6f835d1190a01dfec90961166d1d92836419900`
- Metadata: `metadata__func_pm_remove_cond__ty8un4e6.json`
  - Run 1 SHA-256: `d31e5e0e6072ce2b1d4fde0dbb2dc5371045240cdb173106f1960ad16de3104c`
  - Run 2 SHA-256: `d31e5e0e6072ce2b1d4fde0dbb2dc5371045240cdb173106f1960ad16de3104c`

### Audit Discovery & Fix
The audit discovered that `swesmith` procedural modifiers maintain their own `self.rand = random.Random(24)` at import time. Seeding only Python's global `random` caused in-process state drift. The protocol now enforces per-run reseeding of all modifier instances (`reseed_all(seed)`), guaranteeing 100% deterministic reproducibility across arbitrary runs.
