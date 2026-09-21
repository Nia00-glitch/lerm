import json
import sys
import time
import subprocess
from lerm.adapters.openhands import OpenHandsAgent, _request

sys.stdout.reconfigure(encoding='utf-8')
agent = OpenHandsAgent()
instruction = "list files in /workspace/project using bash"
model = "openrouter/thinkingmachines/inkling-small:free"
active_sb = "oh-agent-server-AajqxBVbQlFXJphnMXMcS"

print(f"Starting isolated smoke test with model: {model}")
subprocess.run(["docker", "unpause", active_sb], capture_output=True)

cid = agent.start_conversation(
    instruction=instruction,
    model=model,
    workspace="",
    extra={"sandbox_id": active_sb}
)
print(f"Conversation ID: {cid}")

send_body = {
    "role": "user",
    "content": [{"type": "text", "text": instruction}],
    "run": True
}

for attempt in range(5):
    time.sleep(1.5)
    subprocess.run(["docker", "unpause", active_sb], capture_output=True)
    status, resp = _request(
        f"{agent.base_url}/api/v1/app-conversations/{cid}/send-message",
        method="POST",
        body=send_body,
        timeout=60.0
    )
    if status < 400:
        print(f"Send message succeeded on attempt {attempt}: status {status}")
        break

# Poll events until ActionEvent occurs or 120s
deadline = time.time() + 120
action_found = False
while time.time() < deadline:
    time.sleep(3)
    subprocess.run(["docker", "unpause", active_sb], capture_output=True)
    evs = agent.events(cid)
    for e in evs:
        if e.get("kind") == "ActionEvent" or (e.get("action") and e.get("source") == "agent"):
            print(f"Found ActionEvent! (total events so far: {len(evs)})")
            action_found = True
            break
        # Also check if MessageEvent has tool_calls
        if e.get("kind") == "MessageEvent" and e.get("llm_message", {}).get("tool_calls"):
            print(f"Found MessageEvent with tool_calls! (total events: {len(evs)})")
            action_found = True
            break
    if action_found:
        break

events = agent.events(cid)
print(f"\nTotal events captured: {len(events)}")
with open("smoke_events_inkling.json", "w", encoding="utf-8") as f:
    json.dump(events, f, indent=2)

for idx, e in enumerate(events):
    kind = e.get("kind")
    src = e.get("source")
    if kind == "ActionEvent" or e.get("action") or (e.get("kind") == "MessageEvent" and e.get("llm_message", {}).get("tool_calls")):
        print(f"\n================ RAW ACTION EVENT (Index {idx}) ================")
        print(json.dumps(e, indent=2))
