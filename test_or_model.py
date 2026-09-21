import urllib.request
import json

# Read API key from /.openhands/settings.json inside container or env
import subprocess
out = subprocess.run(["docker", "exec", "openhands-app", "cat", "/.openhands/settings.json"], capture_output=True, text=True)
settings = json.loads(out.stdout)
or_key = settings.get("llm_profiles", {}).get("profiles", {}).get("openrouter_openrouter_free", {}).get("api_key")
if not or_key:
    # try agent_settings
    or_key = settings.get("agent_settings", {}).get("llm", {}).get("api_key")

print("Found key:", bool(or_key))

models_to_test = [
    "thinkingmachines/inkling-small-20260730:free",
    "thinkingmachines/inkling-small:free",
    "thinkingmachines/inkling-small-20260730",
    "openrouter/free",
]

for m in models_to_test:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {or_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://docs.all-hands.dev/",
            "X-Title": "OpenHands",
        },
        data=json.dumps({
            "model": m,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }).encode("utf-8")
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"Model {m}: SUCCESS! Returned model: {data.get('model')}")
    except urllib.error.HTTPError as e:
        print(f"Model {m}: HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"Model {m}: ERROR {e}")
