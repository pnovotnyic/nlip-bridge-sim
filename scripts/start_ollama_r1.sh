#!/bin/bash
set -e

# SCRIPT_DIR is workspace/scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Quitting any running Ollama applications..."
osascript -e 'tell application "Ollama" to quit' 2>/dev/null || true
killall Ollama 2>/dev/null || true
killall ollama 2>/dev/null || true
sleep 2

echo "Loading defaults from config/models.yaml..."
# Parse defaults using python
eval "$(python3 -c "
import yaml
with open('$ROOT_DIR/experiments/config/models.yaml') as f:
    data = yaml.safe_load(f)
    serving = data['rungs']['R1'].get('serving', {})
    for k, v in serving.items():
        print(f'export {k}=\"\${{{k}:-{v}}}\"')
")"

# Override with positional arguments (e.g. OLLAMA_NUM_PARALLEL=1)
for arg in "$@"; do
    if [[ "$arg" =~ ^[A-Za-z0-9_]+=.*$ ]]; then
        export "$arg"
    fi
done

echo "Starting ollama serve..."
mkdir -p "$ROOT_DIR/experiments/.backends"
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Start server
nohup ollama serve > "$ROOT_DIR/experiments/.backends/ollama.log" 2>&1 &
OLLAMA_PID=$!

# Wait for server to be ready
echo "Waiting for Ollama to start (PID: $OLLAMA_PID)..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:11434/api/tags >/dev/null; then
        break
    fi
    sleep 1
done

if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null; then
    echo "Error: Ollama failed to start. Check experiments/.backends/ollama.log."
    exit 1
fi

echo "Loading nlip-qwen3-4b with keep_alive forever..."
curl -s -d '{"model": "nlip-qwen3-4b", "prompt": "", "keep_alive": -1}' http://127.0.0.1:11434/api/generate >/dev/null

echo "Writing serving.json..."
python3 -c "
import json, os, subprocess
variables = {k: os.environ.get(k) for k in ['OLLAMA_FLASH_ATTENTION', 'OLLAMA_KV_CACHE_TYPE', 'OLLAMA_NUM_PARALLEL', 'OLLAMA_KEEP_ALIVE'] if k in os.environ}
ps_output = subprocess.run(['ollama', 'ps'], capture_output=True, text=True).stdout.strip()
data = {
    'variables': variables,
    'pid': int('$OLLAMA_PID'),
    'start_time': '$START_TIME',
    'ollama_ps': ps_output
}
with open('$ROOT_DIR/experiments/.backends/serving.json', 'w') as f:
    json.dump(data, f, indent=2)
"

echo "Ollama server started and model loaded successfully!"
ollama ps
