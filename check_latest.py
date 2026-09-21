import urllib.request
import json

cid = "557b33349fb54f598b7aea4aa8335937"
req = urllib.request.Request(f"http://127.0.0.1:3000/api/v1/conversation/{cid}/events/search")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
items = data.get("items", [])
for i in range(len(items)-10, len(items)):
    e = items[i]
    print(f"[{i}] {e.get('kind')} ({e.get('source')}): {str(e)[:300]}")
