import subprocess
import json

script = """
import json
for fname in ['event-00004-8502409d-13bb-4c41-b559-94f51de15418.json', 'event-00011-b4c73a49-08ba-42cd-813d-004c9308227a.json']:
    p = f'/workspace/conversations/0e7c9153f82642eba70898f1a5b15255/events/{fname}'
    print('===', fname, '===')
    d = json.load(open(p))
    print(json.dumps(d, indent=2))
"""

out = subprocess.check_output(
    ['docker', 'exec', 'oh-agent-server-4HZ7pXNof2iZ3VlupptCwF', 'python3', '-c', script],
    text=True
)
print(out)
