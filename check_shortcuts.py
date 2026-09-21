import urllib.request
import json

cid = '557b33349fb54f598b7aea4aa8335937'
req = urllib.request.Request(f'http://127.0.0.1:3000/api/v1/conversation/{cid}/events/search')
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
items = data.get('items', [])
for i, e in enumerate(items):
    t_text = str(e).lower()
    if 'rm ' in t_text and 'test' in t_text:
        print(f"Event {i} {e.get('kind')} (source: {e.get('source')}): {str(e)[:250]}")
