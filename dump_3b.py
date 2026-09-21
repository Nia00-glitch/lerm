import json

with open("smoke_events_3b.json", "r", encoding="utf-8") as f:
    evs = json.load(f)

print(f"Total events: {len(evs)}")
for i, e in enumerate(evs):
    kind = e.get("kind")
    src = e.get("source")
    print(f"Event {i}: kind={kind} source={src}")
    if src == "agent" or kind in ("ActionEvent", "MessageEvent"):
        print(json.dumps(e, indent=2))
