import yaml
from lerm.firewall import compute_fixture_hash

for tid in ["HOLDOUT-001", "HOLDOUT-002", "HOLDOUT-003", "HOLDOUT-004"]:
    with open(f"holdout/tasks/{tid}.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    print(f'"{tid}": "{compute_fixture_hash(data)}"')
