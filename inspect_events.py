import subprocess
import json

script = """
import glob, json
for f in sorted(glob.glob('/workspace/conversations/0e7c9153f82642eba70898f1a5b15255/events/event-*.json')):
    d = json.load(open(f))
    kind = d.get('kind')
    source = d.get('source')
    summary = ''
    if 'llm_message' in d:
        summary = str(d['llm_message'].get('content', ''))[:100]
    elif 'action' in d:
        summary = str(d['action'])[:100]
    elif 'observation' in d:
        summary = str(d['observation'])[:100]
    elif 'tool_name' in d:
        summary = f"tool={d.get('tool_name')} call={str(d.get('tool_call'))[:60]}"
    print(f"{f.split('/')[-1]}: kind={kind} source={source} summary={summary!r}")
"""

out = subprocess.check_output(
    ['docker', 'exec', 'oh-agent-server-4HZ7pXNof2iZ3VlupptCwF', 'python3', '-c', script],
    text=True
)
print(out)
