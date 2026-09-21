import subprocess
import json

script = """
import json

with open('/.openhands/settings.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Change model to qwen2.5-coder:14b
data['agent_settings']['llm']['model'] = 'ollama/qwen2.5-coder:14b'
data['llm_profiles']['profiles']['Ollama']['model'] = 'ollama/qwen2.5-coder:14b'

with open('/.openhands/settings.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print('Updated /.openhands/settings.json to ollama/qwen2.5-coder:14b')
"""

out = subprocess.check_output(
    ['docker', 'exec', 'openhands-app', 'python3', '-c', script],
    text=True
)
print(out)
