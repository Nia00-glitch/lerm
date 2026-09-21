import json

data = json.load(open("sampled_agent_actions.json", encoding="utf-8"))

for i, item in enumerate(data):
    prompts = item.get("prompts", [])
    p0 = prompts[0] if prompts else ""
    p1 = prompts[1] if len(prompts) > 1 else ""
    cid = item["cid"]
    print(f"\n==================== SAMPLE {i+1} (cid: {cid}) ====================")
    print("Turn 0 Prompt:", p0[:120])
    if p1:
        print("Turn 1 Prompt:", p1[:120])
    actions = item.get("actions", [])
    print(f"Total matching actions: {len(actions)}")
    for j, a in enumerate(actions[:4]):
        cmd = a.get("cmd") or a.get("args") or ""
        print(f"  [Act {j+1}]: {cmd[:250]}")
