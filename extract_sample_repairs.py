import glob
import json
import os

def dump_conv(cid, label):
    cdir = f"/.openhands/v1_conversations/{cid}"
    efiles = sorted(glob.glob(f"{cdir}/*.json"), key=os.path.getmtime)
    print(f"\n{'='*80}\n[{label}] Conversation {cid}\n{'='*80}")
    turn = 0
    for ef in efiles:
        try:
            ev = json.load(open(ef))
            src = ev.get("source")
            kind = ev.get("kind")
            if src == "user":
                txt = str(ev.get("llm_message", {}).get("content", ""))
                if "In-loop verification failed" in txt:
                    print(f"\n--- USER REPAIR PROMPT (Turn {turn}) ---")
                    print(txt[:300] + "...")
                    turn += 1
                elif "Your previous attempt did not resolve" in txt:
                    print(f"\n--- USER RETRY PROMPT (Turn {turn}) ---")
                    print(txt[:300] + "...")
                    turn += 1
                else:
                    print(f"\n--- USER INITIAL PROMPT ---")
                    print(txt[:200] + "...")
            if kind == "ActionEvent" or ev.get("action"):
                act = ev.get("action", {})
                cmd = act.get("command") or ""
                tc = ev.get("tool_call", {}) or {}
                args = tc.get("arguments") or ""
                # Print commands that write or edit files
                if any(w in cmd for w in ["cat >", "sed", "echo", "python", "rm "]) or any(w in args for w in ["cat >", "sed", "str_replace"]):
                    print(f"\n--- AGENT ACTION EVENT ---")
                    if cmd:
                        print("COMMAND:\n" + cmd[:600])
                    if args:
                        print("ARGS:\n" + args[:600])
        except Exception as e:
            pass

# Let's inspect:
# 1. HOLDOUT-003: 54826bd2ed3246c3b290cdac0ffe13f9 (loop_verify, turns=2)
# 2. HOLDOUT-002: 0792a4808f4e4f06ba376280cc133fd8 (loop_verify, turns=2)
# 3. HOLDOUT-004: 957acaee818a4a7d9cf165ee9c1e5afe (loop_retry)
# 4. HOLDOUT-001: d8987259a63a4900b6f0c3516f5c5a3b (calc.py)
dump_conv("54826bd2ed3246c3b290cdac0ffe13f9", "TRIAL 1: HOLDOUT-003 | loop_verify | Turns=2")
dump_conv("0792a4808f4e4f06ba376280cc133fd8", "TRIAL 2: HOLDOUT-002 | loop_verify | Turns=2")
dump_conv("957acaee818a4a7d9cf165ee9c1e5afe", "TRIAL 3: HOLDOUT-004 | loop_retry | Turns=2")
dump_conv("d8987259a63a4900b6f0c3516f5c5a3b", "TRIAL 4: HOLDOUT-001 | loop_retry | Turns=1")
