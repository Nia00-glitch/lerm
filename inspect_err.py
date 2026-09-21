import json

with open("smoke_events.json", "r", encoding="utf-8") as f:
    evs = json.load(f)

for i, e in enumerate(evs):
    kind = e.get("kind")
    src = e.get("source")
    print(f"Event {i}: kind={kind} source={src}")
    if src == "agent" or "error" in kind.lower() or "error" in str(e).lower():
        print(json.dumps(e, indent=2))
