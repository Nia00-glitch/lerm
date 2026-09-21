import subprocess
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

containers = {
    '911b6ad8d0ac': 'b912000f84814a739ce4a6bd5d4d6a74',
    '3fda9f267eb3': 'e3ba0352df234dc1b863ed2947b506fc',
    'b3c902bd905f': '34b7702b8f184feb901e074bc2b5b14d',
    'd3e58357f63e': '90c9ef45fa594674bcf568fd54b1938b',
    '5ce2e13c4471': '73492a556d4a40e5b00fb5349863a532',
    'e4acbe41bd5f': '655febb6ffb747e98c112b1fe89f4a51',
    'b3f7d2fe9a5d': '4e04814f62834b6a9473b007efc156cd',
    '19c3fe62fd41': '0e7c9153f82642eba70898f1a5b15255'
}

for cid, conv in containers.items():
    meta_raw = subprocess.run(['docker', 'exec', cid, 'cat', f'/workspace/conversations/{conv}/meta.json'], capture_output=True, encoding='utf-8', errors='replace')
    model = "unknown"
    if meta_raw.stdout:
        try:
            m = json.loads(meta_raw.stdout)
            model = m.get('llm_model') or m.get('agent', {}).get('llm', {}).get('model')
        except Exception:
            pass
            
    events_raw = subprocess.run(['docker', 'exec', cid, 'ls', f'/workspace/conversations/{conv}/events'], capture_output=True, encoding='utf-8', errors='replace')
    event_files = events_raw.stdout.strip().split()
    actions = []
    for ef in event_files:
        if not ef.endswith('.json'):
            continue
        content = subprocess.run(['docker', 'exec', cid, 'cat', f'/workspace/conversations/{conv}/events/{ef}'], capture_output=True, encoding='utf-8', errors='replace')
        try:
            ed = json.loads(content.stdout)
            kind = ed.get('kind')
            if kind in ('ActionEvent', 'Action') or 'action' in ed or ed.get('llm_message', {}).get('tool_calls'):
                actions.append((ef, kind, ed))
        except Exception:
            pass
    print(f"Container {cid[:12]} | Conv {conv[:12]} | Model: {model} | Total Events: {len(event_files)} | Actions: {len(actions)}")
    for ef, kind, ed in actions:
        print(f"  -> {ef} ({kind}): {str(ed)[:200]}")
