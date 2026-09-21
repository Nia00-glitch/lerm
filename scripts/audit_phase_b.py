import os
import sys
from pathlib import Path
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lerm.firewall import verify_manifest_admission, verify_dataset_separation, FirewallViolation

print("=================================================================")
print("=== PHASE B: ADVERSARIAL HISTORICAL FIREWALL AUDIT ===")
print("=================================================================\n")

# B2: Four historical tasks tested against primary
print("--- B2: TESTING ALL FOUR HISTORICAL TASKS AGAINST PRIMARY ---")
historical_tasks = ["HOLDOUT-001", "HOLDOUT-002", "HOLDOUT-003", "HOLDOUT-004"]
for tid in historical_tasks:
    p = Path(f"holdout/tasks/{tid}.yaml")
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        verify_manifest_admission(data, target_role="primary")
        print(f"[{tid}] UNEXPECTED PASS (Firewall breached!)")
    except FirewallViolation as e:
        print(f"[{tid}] CAUGHT EXPECTED FirewallViolation: {e}")
    except Exception as e:
        print(f"[{tid}] UNEXPECTED EXCEPTION TYPE: {type(e).__name__}: {e}")

# B3: Four historical tasks tested against calibration
print("\n--- B3: TESTING HISTORICAL TASKS AGAINST CALIBRATION ---")
for tid in historical_tasks:
    p = Path(f"holdout/tasks/{tid}.yaml")
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        verify_manifest_admission(data, target_role="calibration")
        print(f"[{tid}] ADMITTED to calibration! (target_role=calibration)")
    except FirewallViolation as e:
        print(f"[{tid}] REJECTED from calibration: {e}")

# B4: Positive control
print("\n--- B4: POSITIVE CONTROL (CLEAN FRESH CANDIDATE) ---")
fresh_candidate = {
    "id": "SWE-SM-001",
    "data_role": "primary",
    "historical_exposure": False,
    "primary_exp_loop_003_eligible": True,
    "provenance": {"repo": "mewwts__addict.75284f95", "commit": "affe22e"}
}
try:
    verify_manifest_admission(fresh_candidate, target_role="primary")
    print("[SWE-SM-001] ADMITTED to primary cleanly (Expected behavior)")
except Exception as e:
    print(f"[SWE-SM-001] UNEXPECTED REJECTION: {e}")

# B5: Metadata tampering attacks on HOLDOUT-001
print("\n--- B5: METADATA TAMPERING ATTACKS (ON HOLDOUT-001) ---")
with open("holdout/tasks/HOLDOUT-001.yaml", "r", encoding="utf-8") as f:
    base_data = yaml.safe_load(f)

# Attack 1: historical_exposure = False, data_role = primary, but primary_exp_loop_003_eligible left False
a1_data = dict(base_data)
a1_data["historical_exposure"] = False
a1_data["data_role"] = "primary"
try:
    verify_manifest_admission(a1_data, target_role="primary")
    print("Attack 1 (historical_exposure=False): BREACHED / ADMITTED!")
except FirewallViolation as e:
    print(f"Attack 1 (historical_exposure=False): CAUGHT REJECTION -> {e}")

# Attack 2: primary_exp_loop_003_eligible = True, data_role = primary, but historical_exposure left True
a2_data = dict(base_data)
a2_data["primary_exp_loop_003_eligible"] = True
a2_data["data_role"] = "primary"
try:
    verify_manifest_admission(a2_data, target_role="primary")
    print("Attack 2 (eligible=True): BREACHED / ADMITTED!")
except FirewallViolation as e:
    print(f"Attack 2 (eligible=True): CAUGHT REJECTION -> {e}")

# Attack 3: Tamper BOTH flags (historical_exposure=False, primary_exp_loop_003_eligible=True, data_role=primary)
a3_data = dict(base_data)
a3_data["historical_exposure"] = False
a3_data["primary_exp_loop_003_eligible"] = True
a3_data["data_role"] = "primary"
try:
    verify_manifest_admission(a3_data, target_role="primary")
    print("Attack 3 (Both flags tampered to look fresh, ID='HOLDOUT-001'): BREACHED / ADMITTED! (VULNERABILITY!)")
except FirewallViolation as e:
    print(f"Attack 3 (Both flags tampered): CAUGHT REJECTION -> {e}")

# Attack 4: Copy into new filename & change ID
a4_data = dict(base_data)
a4_data["id"] = "FAKE-FRESH-001"
a4_data["historical_exposure"] = False
a4_data["primary_exp_loop_003_eligible"] = True
a4_data["data_role"] = "primary"
try:
    verify_manifest_admission(a4_data, target_role="primary")
    print("Attack 4 (Copied task with ID='FAKE-FRESH-001'): BREACHED / ADMITTED! (VULNERABILITY!)")
except FirewallViolation as e:
    print(f"Attack 4 (Copied task): CAUGHT REJECTION -> {e}")

# B6: Trace-ingestion attack
print("\n--- B6: TRACE INGESTION ATTACK ---")
# Trace with task_id HOLDOUT-001 but data_role labeled "primary"
spoofed_trace = [
    {"run_id": "run-spoof-001", "task_id": "HOLDOUT-001", "data_role": "primary", "condition": "loop_verify"}
]
try:
    verify_dataset_separation(spoofed_trace, expected_role="primary")
    print("B6 Trace Ingestion (HOLDOUT-001 with data_role='primary'): ACCEPTED! (VULNERABILITY: No task-level firewall at trace ingestion!)")
except FirewallViolation as e:
    print(f"B6 Trace Ingestion: CAUGHT REJECTION -> {e}")

# B10: Fail-closed audit
print("\n--- B10: FAIL-CLOSED AUDIT ---")
# Q1 & Q2: Missing flags
q1_data = {"id": "UNTAGGED-TASK-001", "data_role": "primary"}
try:
    verify_manifest_admission(q1_data, target_role="primary")
    print("Q1/Q2 (Missing historical_exposure & primary_exp_loop_003_eligible): ADMITTED! (FAILS OPEN!)")
except FirewallViolation as e:
    print(f"Q1/Q2: REJECTED -> {e}")

# Q3: String booleans
q3_data = {"id": "STR-BOOL-TASK", "data_role": "primary", "historical_exposure": "false", "primary_exp_loop_003_eligible": "true"}
try:
    verify_manifest_admission(q3_data, target_role="primary")
    print("Q3 (String booleans 'false' / 'true'): ADMITTED! (FAILS OPEN!)")
except FirewallViolation as e:
    print(f"Q3: REJECTED -> {e}")
