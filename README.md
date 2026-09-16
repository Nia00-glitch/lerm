# LERM — Loop Engineering Research Machine

Control plane for a 24/7 experimental lab on agent loops. The output is not an agent; it is
verified, reproducible, falsifiable knowledge about loops, plus the knowledge base it
accumulates. Truth > throughput > compounding, in that order.

Built against `docs/SPEC.md`. Where this repo deviates from the spec, `docs/DEVIATIONS.md`
says so and why — nothing is silently changed.

## Status — honest

| Phase | State | Note |
|---|---|---|
| P0 execution plane | **ADR written, gate implemented, NOT VERIFIED** | needs a Docker daemon; `make preflight` decides |
| P1 trace + store | **built and exercised** | JSONL -> DuckDB (SQLite fallback), three-field outcomes |
| P2 HAL/Inspect harness | **adapter only** | `lerm/adapters/openhands.py` drives OpenHands+OmniRoute; harness wiring needs P0 green |
| P3 parallel plane | **not built** | Ray/SkyPilot/warm pool; needs P0 + real hardware |
| P4 experiment compiler | **built** | power analysis, sealed prereg, pass^k, effect+CI |
| P5 adversarial skeptic | **built and passing its acceptance test** | `make selftest` — kills 3 planted spurious findings, spares the honest one |
| P6 knowledge base | **built** | schema enforced in code; held-out set scaffolded, tasks to author |
| P7 direction finder | **not built** | OpenAlex + PaperQA2, needs network |
| P8 24/7 controller | **not built** | guardrails (spend cap, kill switch, drift canary, digest) are built and wired |

Everything marked built runs offline, today, with `numpy scipy pandas PyYAML`.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in OMNIROUTE_API_KEY and a pinned LLM_MODEL
set -a && source .env && set +a

make selftest   # P5 acceptance, offline, ~2s
make demo       # full offline pipeline; writes real artifacts to every directory
make preflight  # P0 gate on your execution plane — expect FAILs until WSL2+Docker is up
```

`make demo` output ends at `status=UNCERTAIN`, not `SUPPORTED`. That is correct: skeptic
attacks 1 and 4 need the execution plane, and the machine never promotes a finding whose
attacks were merely skipped.

## The parts that matter

- **`lerm/stats.py`** — `pass^k` via the unbiased hypergeometric estimator, effect sizes with
  a task-level bootstrap CI (bootstrapping runs instead of tasks is how agent papers get CIs
  that are far too narrow), power analysis on the `pass^k` scale, O'Brien-Fleming boundaries
  for legal early stopping, and verifier FAR/FRR.
  Budget **n_reruns ≥ 2k**: at `n == k` the estimator collapses to a per-task 0/1 and the CI
  explodes. The test suite has this planted as a regression.
- **`lerm/prereg.py`** — sealed, hash-verified, refuses overwrite. `assert_declared()` gates
  every analysis; an undeclared metric raises instead of quietly becoming a headline.
- **`lerm/trace.py`** — `agent_claimed` / `verifier_said` / `ground_truth` are three separate
  fields and `verified_success()` never falls back to the agent's own claim. Infra failures
  are excluded from success rates and counted separately.
- **`lerm/confounds.py`** — ten mechanical checks (compute, tokens, attempts, cost, model
  version, fingerprint drift, task order, seed policy, task set, human intervention). Any
  failure downgrades the claim to CORRELATIONAL.
- **`lerm/skeptic.py`** — five attacks. Refuses at construction time to review a model from
  its own family. Attacks needing execution return `NEEDS_EXECUTION`, never a silent pass.
  Track `kill_rate()` — trending to 0% means the skeptic has degraded.
- **`lerm/kb.py`** — `unexplained` is mandatory and non-empty; hedging words are rejected;
  `already_settled()` blocks re-running a settled hypothesis; principles need ≥2 model
  families, a replication, a clean confound check **and** human sign-off.
- **`lerm/guardrails.py`** — spend ledger with hard stop, kill-switch file, model drift canary.
  Wire the cap at P2, not P8.

## What you have to do that code can't

1. Resolve P0 on your host (WSL2 + Docker Engine + systemd). `make preflight` tells you when.
2. Pin a current model ID. `LLM_MODEL=anthropic/claude-3-5-sonnet-20240620` is a 2024 model;
   `scripts/preflight.py` fails the build on it.
3. Author the private held-out set — see `holdout/README.md`. 60–120 tasks. This is the single
   highest-leverage artifact in the whole plan and it cannot be generated from here.

## Layout

```
lerm/          control-plane library (stats, prereg, trace, confounds, skeptic, kb, guardrails, digest)
lerm/adapters/ OpenHands + OmniRoute drivers (stdlib http only, works on bare python)
scripts/       preflight.py (P0 gate), demo_offline.py (end-to-end dry run)
tests/         P5 acceptance + regression suite
docs/          SPEC.md, ADR-0001, DEVIATIONS.md
holdout/       private held-out set: schema, authoring guide, seed tasks
preregistrations/ findings/ negative_results/ reports/daily/ traces/ store/   artifacts
```
