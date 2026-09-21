import json
import sys
import time
import subprocess
from lerm.adapters.openhands import OpenHandsAgent, _request

sys.stdout.reconfigure(encoding='utf-8')
agent = OpenHandsAgent()
instruction = "list the files in /workspace/project using bash"
model = "ollama/qwen2.5-coder:3b"

print(f"Starting 3b smoke test with model: {model}")
cid = agent.start_conversation(instruction=instruction, model=model, workspace="")
print(f"Conversation ID: {cid}")

sandbox_id = agent.get_sandbox(cid)
if sandbox_id:
    subprocess.run(["docker", "unpause", sandbox_id], capture_output=True)
    print(f"Sandbox container: {sandbox_id}")

send_body = {
    "role": "user",
    "content": [{"type": "text", "text": instruction}],
    "run": True
}

# Send message
status, resp = _request(f"{agent.base_url}/api/v1/app-conversations/{cid}/send-message", method="POST", body=send_body, timeout=120.0)
print(f"Send message status: {status}")

# Poll events until agent responds or 120s
deadline = time.time() + 120
while time.time() < deadline:
    time.sleep(4)
    if sandbox_id:
        subprocess.run(["docker", "unpause", sandbox_id], capture_output=True)
    evs = agent.events(cid)
    agent_msg = [e for e in evs if e.get("source") == "agent" and e.get("kind") == "MessageEvent"]
    if agent_msg:
        print("Agent responded!")
        break
    # check execution_status
    try:
        s, body = _request(f"{agent.base_url}/api/v1/app-conversations?ids={cid}")
        if s < 400 and body and isinstance(body, list):
            st = str(body[0].get("execution_status") or body[0].get("status") or "").lower()
            if st in {"finished", "completed", "error", "idle", "paused"}:
                break
    except Exception:
        pass

events = agent.events(cid)
print(f"\nTotal events captured: {len(events)}")
for idx, e in enumerate(events):
    kind = e.get("kind")
    src = e.get("source")
    print(f"\n--- EVENT {idx}: {kind} (source: {src}) ---")
    if e.get("llm_message"):
        print("llm_message:", json.dumps(e.get("llm_message"), indent=2))
    elif e.get("action"):
        print("action:", json.dumps(e.get("action"), indent=2))
    else:
        print(json.dumps({k: v for k, v in e.items() if k not in ("id", "timestamp")}, indent=2)[:300])

with open("smoke_events_3b.json", "w", encoding="utf-8") as f:
    json.dump(events, f, indent=2)
print("\nWrote smoke_events_3b.json")
