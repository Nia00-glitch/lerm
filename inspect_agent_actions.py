import glob
import json
import os
import subprocess

# Inspect conversation events from openhands container
cmd = """python3 -c '
import glob, json, os

conv_dirs = sorted(glob.glob("/.openhands/v1_conversations/*"), key=os.path.getmtime, reverse=True)

samples = []
for cdir in conv_dirs:
    cid = os.path.basename(cdir)
    event_files = sorted(glob.glob(cdir + "/*.json"), key=os.path.getmtime)
    actions = []
    user_prompts = []
    for ef in event_files:
        try:
            with open(ef) as f:
                ev = json.load(f)
            if ev.get("source") == "user":
                content = ev.get("llm_message", {}).get("content", [])
                if isinstance(content, list) and content:
                    user_prompts.append(content[0].get("text", ""))
                elif isinstance(content, str):
                    user_prompts.append(content)
            if ev.get("kind") == "ActionEvent" or ev.get("action"):
                act = ev.get("action") or {}
                c = act.get("command") or ""
                tc = ev.get("tool_call", {}) or {}
                args = tc.get("arguments") or ""
                if any(k in c for k in ["cat", "sed", "python", "echo", "nano", "tee"]) or any(k in args for k in ["cat", "sed", "python", "echo"]):
                    actions.append({"cmd": c, "args": args, "raw": ev})
        except Exception:
            pass
    if actions:
        samples.append({
            "cid": cid,
            "prompts": user_prompts,
            "actions": actions
        })
    if len(samples) >= 20:
        break

print(json.dumps(samples[:10]))
'"""

res = subprocess.run(["docker", "exec", "6bdfc7340808", "sh", "-c", cmd], capture_output=True, text=True)
if res.returncode != 0:
    print("Error:", res.stderr)
else:
    data = json.loads(res.stdout)
    print(f"Loaded {len(data)} sample conversations with action events.")
    with open("sampled_agent_actions.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Wrote sampled_agent_actions.json")
