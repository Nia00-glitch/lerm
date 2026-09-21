from lerm.prereg import Preregistration, verify

p = Preregistration(
    id="EXP-LOOP-002",
    hypothesis="In-loop verification and repair (loop_verify) yields a higher pass^5 verified success rate than compute-matched naive retry (loop_retry) under matched token, turn, and wallclock budgets on held-out code repair tasks.",
    conditions=["loop_retry", "loop_verify"],
    primary_metric="verified_success_pass_k",
    secondary_metrics=["reliability_gap", "verifier_false_accept_rate", "total_tokens", "wallclock_s"],
    n_tasks=4,
    k_reruns=5,
    n_reruns=10,
    tasks_public=[],
    private_holdout_n=4,
    models=["openrouter/thinkingmachines/inkling-small:free"],
    decision_threshold=0.05,
    alpha=0.05,
    power=0.80,
    stopping_rule="fixed_sample_size_k5_n10",
    compute_matching="loop_verify is attempt-, token-, and wallclock-matched to loop_retry under a fixed turn ceiling of 3 turns, max token budget of 16000 tokens, and hard wallclock cap of 120.0s per trial enforced by controller",
    predicted_failure_mode="loop_verify fails to diagnose subtle test failures or burns turns; n_tasks=4 keeps bootstrap CI wide regardless of reruns — this experiment is a pilot for pipeline validity, not yet powered for a general causal claim.",
)

path = p.seal()
print(f"Successfully sealed preregistration: {path}")
verified = verify("EXP-LOOP-002")
print(f"Verified content hash: {verified.get('content_hash')}")
