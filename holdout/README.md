# Private held-out set

60–120 tasks that are **not on the public internet**. This is what makes results credible when
every public benchmark may be in training data (§5.5, §6). Publish aggregate scores only;
never publish the tasks.

## Categories (roughly equal counts)

1. **Recovery after induced failure** — the environment breaks mid-task on purpose (a tool
   returns a plausible-but-wrong result, a file vanishes, a dependency is pinned to a broken
   version). Measures whether the loop notices and re-plans, which is the core loop-engineering
   question.
2. **Long-horizon state tracking** — the answer depends on something established 30+ steps
   earlier and never restated. Measures memory scaffold, not model recall.
3. **Tool misuse traps** — a tool that looks right for the job and silently corrupts state.
   The correct behaviour is to not use it, so an agent that "succeeds" fast has failed.
4. **Unreliable verifier** — the in-loop verifier is wrong ~15% of the time by construction and
   ground truth is known separately. This is the only way to measure verifier FAR honestly.

## Rules

- Author them yourself; do not generate them with a frontier model that may later be under test.
- Store encrypted at rest (`age` or `gpg`); the decryption key never lives in the repo.
- `task.yaml` per task, schema in `holdout/tasks/_schema.yaml`.
- Every task needs a **programmatic** ground-truth checker that does not read the agent's claim.
- Run a shortcut pilot on every new task before it joins the set (§5.4). If a small agent passes
  without solving, fix the task, not the result.
