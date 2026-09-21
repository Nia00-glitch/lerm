import subprocess

# Save current working tree versions
with open('scripts/run_live_lerm.py', 'r', encoding='utf-8') as f:
    cur_live = f.read()
with open('lerm/ledger.py', 'r', encoding='utf-8') as f:
    cur_ledger = f.read()

# Write old versions
old_ledger = cur_ledger.replace(
    'regression_result: dict[str, Any] | None = None',
    'regression_result: dict[str, Any]'
)
new_dict_block = """        d = asdict(self)
        if self.regression_result is None:
            d.pop("regression_result", None)
        return d"""
old_ledger = old_ledger.replace(new_dict_block, "        return asdict(self)")
with open('lerm/ledger.py', 'w', encoding='utf-8') as f:
    f.write(old_ledger)

old_live = cur_live.replace(
    'regression_result=None,',
    'regression_result=reg_report.to_dict(),'
)
with open('scripts/run_live_lerm.py', 'w', encoding='utf-8') as f:
    f.write(old_live)

# Stage old versions
subprocess.run(['git', 'add', 'lerm/ledger.py', 'scripts/run_live_lerm.py'], check=True)

# Restore new versions in working tree
with open('scripts/run_live_lerm.py', 'w', encoding='utf-8') as f:
    f.write(cur_live)
with open('lerm/ledger.py', 'w', encoding='utf-8') as f:
    f.write(cur_ledger)
print("Staged baseline and restored fixed versions.")
