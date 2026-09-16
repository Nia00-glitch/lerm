# SPEC

The canonical build spec is your own file, "BUILD SPEC / MASTER PROMPT — Loop Engineering
Research Machine (LERM)". **Drop it in here as `docs/SPEC.md`, replacing this placeholder,
and commit it** — OpenHands should read the spec from the repo, not from a chat paste, so the
spec is versioned alongside the code it produced.

Non-negotiables this repo enforces in code (not in prose):

- §1.1 no fake sandbox — `scripts/preflight.py` exits 1 rather than proceed without Docker
- §4 overhead budget — `trace.median_overhead_ratio()`, surfaced in the daily digest
- §5.1 three outcome fields, never merged — `trace.RunRecord`
- §5.2 pass^k with k>=5 — `stats.pass_hat_k`, enforced in `prereg.Preregistration`
- §5.3 sealed preregistration — `prereg.seal/verify/assert_declared`
- §5.6 automated confound checklist — `confounds.check_conditions`
- §5.7 three-valued outcomes, no hedging — `kb.Finding.__post_init__`
- §5.8 model drift canary — `guardrails.check_drift`
- §7 five skeptic attacks, different model family — `skeptic.Skeptic`
- §8 `unexplained` mandatory, principles need human sign-off — `kb.Finding`
- §9 spend cap + kill switch + daily digest — `guardrails`, `digest`
