import urllib.request
import json

cid = "557b33349fb54f598b7aea4aa8335937"
req = urllib.request.Request(f"http://127.0.0.1:3000/api/v1/conversation/{cid}/events/search")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
items = data.get("items", [])
print(f"Total events in trial conversation: {len(items)}")
for i, e in enumerate(items):
    kind = e.get("kind")
    src = e.get("source")
    if kind == "ActionEvent" or e.get("action") is not None:
        print(f"[{i}] {kind} ({src}): {e.get('summary') or e.get('action')}")
