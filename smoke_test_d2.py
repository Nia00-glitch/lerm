import json
import sys
import time
import subprocess
from lerm.adapters.openhands import OpenHandsAgent, _request

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
agent = OpenHandsAgent()

def is_real_action(e: dict) -> bool:
    if e.get("kind") in ("ActionEvent", "Action"):
        return True
    if e.get("action") is not None:
        return True
    if e.get("kind") == "MessageEvent" and e.get("source") == "agent":
        if e.get("llm_message", {}).get("tool_calls"):
            return True
        if "tool_call" in e.get("action", {}):
            return True
    return False

def run_smoke(model_name: str):
    instruction = "list the files in /workspace/project using bash"
    print(f"\n==========================================")
    print(f"Starting smoke test with model: {model_name}")
    print(f"==========================================")
    
    cid = agent.start_conversation(instruction=instruction, model=model_name, workspace="")
    print(f"Conversation ID: {cid}")
    
    sandbox_id = agent.get_sandbox(cid)
    if sandbox_id:
        subprocess.run(["docker", "unpause", sandbox_id], capture_output=True)
        print(f"Sandbox container: {sandbox_id}")
    
    # Wait for sandbox server initialization
    send_body = {
        "role": "user",
        "content": [{"type": "text", "text": instruction}],
        "run": True
    }
    
    status = 0
    for attempt in range(6):
        time.sleep(3)
        if sandbox_id:
            subprocess.run(["docker", "unpause", sandbox_id], capture_output=True)
        status, resp = _request(f"{agent.base_url}/api/v1/app-conversations/{cid}/send-message", method="POST", body=send_body, timeout=120.0)
        print(f"Send message attempt {attempt+1}: HTTP {status}")
        if status < 400:
            break
        print(f"  Response: {resp}")
    
    print("Polling for agent actions / completion...")
    action_events = []
    events = []
    for i in range(25): # wait up to 125s
        time.sleep(5)
        if sandbox_id:
            subprocess.run(["docker", "unpause", sandbox_id], capture_output=True)
        events = agent.events(cid)
        action_events = [e for e in events if is_real_action(e)]
        print(f"Poll step {i+1}: {len(events)} total events, {len(action_events)} real action events")
        
        if action_events:
            print(f"--> SUCCESS: Detected {len(action_events)} real tool-call / ActionEvent(s)!")
            break
            
        try:
            status, body = _request(f"{agent.base_url}/api/v1/app-conversations?ids={cid}")
            if status < 400 and body and isinstance(body, list):
                exec_state = str(body[0].get("execution_status") or body[0].get("status") or "").lower()
                if exec_state in {"stopped", "finished", "error", "completed", "paused"}:
                    print(f"Agent finished execution with state: {exec_state}")
                    break
        except Exception:
            pass

    return cid, events, action_events

if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "openrouter/openrouter/free"
    cid, events, actions = run_smoke(model)
    print(f"\nTotal events: {len(events)}")
    print(f"Total action events: {len(actions)}")
    with open("smoke_events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    print("Saved all events to smoke_events.json")
    if actions:
        print("\nRAW ACTION EVENT JSON:")
        print(json.dumps(actions[0], indent=2))
