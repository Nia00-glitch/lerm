import subprocess
import json
import requests

script = """
import json

with open('/.openhands/settings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

pinned_model = 'openrouter/thinkingmachines/inkling-small:free'

# Update profile
prof = data['llm_profiles']['profiles']['openrouter_openrouter_free']
prof['model'] = pinned_model
prof['base_url'] = None
prof['openrouter_site_url'] = 'https://docs.all-hands.dev/'
prof['openrouter_app_name'] = 'OpenHands'

# Also add a named profile for clarity
data['llm_profiles']['profiles']['pinned_inkling'] = dict(prof)

# Update agent_settings
data['agent_settings']['llm'] = dict(prof)

# Set active profile
data['llm_profiles']['active'] = 'pinned_inkling'

with open('/.openhands/settings.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print('Updated settings.json with pinned model:', pinned_model)
"""

out = subprocess.check_output(
    ['docker', 'exec', 'openhands-app', 'python3', '-c', script],
    text=True
)
print(out)

# Also notify OpenHands via activate endpoint or reload settings
try:
    r = requests.post("http://127.0.0.1:3000/api/v1/settings/profiles/pinned_inkling/activate")
    print(f"Activate response: {r.status_code} - {r.text[:200]}")
except Exception as e:
    print("Activate error:", e)

# Update local .env
with open(".env", "r", encoding="utf-8") as f:
    env_content = f.read()

new_lines = []
for line in env_content.splitlines():
    if line.startswith("LLM_MODEL="):
        new_lines.append("LLM_MODEL=openrouter/thinkingmachines/inkling-small:free")
    else:
        new_lines.append(line)

with open(".env", "w", encoding="utf-8") as f:
    f.write("\n".join(new_lines) + "\n")

print("Updated .env with LLM_MODEL=openrouter/thinkingmachines/inkling-small:free")
