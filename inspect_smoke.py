import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('smoke_events.json', 'r', encoding='utf-8') as f:
    events = json.load(f)

print(f"Total events in smoke_events.json: {len(events)}")
for i, e in enumerate(events):
    kind = e.get('kind')
    source = e.get('source')
    summary = ""
    if 'llm_message' in e:
        summary = str(e['llm_message'].get('content', ''))[:100]
    elif 'action' in e:
        summary = str(e['action'])[:100]
    elif 'observation' in e:
        summary = str(e['observation'])[:100]
    elif 'key' in e:
        summary = f"{e.get('key')}={e.get('value')}"
    print(f"Event {i}: kind={kind} source={source} summary={summary!r}")
