from lerm.kb import Finding

neg_finding = Finding(
    id="NEG-LIVE-0001",
    hypothesis="the P0 live pipeline produces trustworthy verified_success records.",
    preregistration="PREREG-LIVE-0001",
    conditions=["live_openhands"],
    tasks={
        "public": ["HOLDOUT-001", "HOLDOUT-002", "HOLDOUT-003", "HOLDOUT-004"],
        "private_holdout_n": 0
    },
    models=["ollama/qwen3:4b-instruct-2507-q4_K_M", "ollama/qwen2.5-coder:14b"],
    n_runs=1,
    k_reruns=5,
    primary_metric="verified_success",
    effect_size={"value": 0.0, "ci_low": 0.0, "ci_high": 0.0},
    false_accept_rate=1.0,
    false_reject_rate=0.0,
    cost={"usd": 0.0, "gpu_hours": 0.0, "wallclock": 0.058},
    confounds_checked=["con_runtime_drift", "con_token_cost"],
    skeptic_attempts=[{
        "attack": "audit_pipeline_integrity",
        "killed": True,
        "reason": "D1: regression_result hardcoded demo data; D2: model emitted raw json without ActionEvent; D3: HOLDOUT-001 passed untouched; D4: checkers missing exit 2; D5: trace timing 52us and 0.0 overhead; D6: shortcut pilot mock placeholder"
    }],
    status="REFUTED",
    scope_limits=(
        "Original LIVE-0001 run artifacts across HOLDOUT-001 through HOLDOUT-004. "
        "Defect D1: regression_result contained static synthetic numbers from unverified dummy tasks T1/T2/T3. "
        "Defect D2: agent model emitted raw JSON text inside message content rather than structured tool actions. "
        "Defect D3: HOLDOUT-001 ground truth checker passed on unmodified fixtures because add() was untested. "
        "Defect D4: checkers for HOLDOUT-002, 003, 004 were never materialized, failing with missing file exit code 2. "
        "Defect D5: trace timing started_utc and ended_utc were 52us apart with 0.0 overhead. "
        "Defect D6: shortcut_pilot blocks were unexecuted scaffolds."
    ),
    unexplained=(
        "How the uninstrumented mock regression_result block and premature status: OBSERVED were committed to "
        "research_ledger.jsonl without failing preflight assertions. Root cause identified in run_live_lerm.py "
        "populating synthetic demo data into production ledger entries."
    ),
    next_questions=[
        "Does the repaired P0 pipeline with tool-calling-capable model and independent ground truth checkers produce verified success records without regression?"
    ],
    causal_verdict="CORRELATIONAL",
    replications=[],
    human_signoff=False,
)

path = neg_finding.save()
print("Saved negative result finding to:", path)
