#!/usr/bin/env bash
# Rebuild stage1/vendor (pinned clones) and stage1/venvs (declared dependencies only; no build scripts of the examples are run).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p vendor venvs
pin() { # name commit
  [ -d "vendor/$1" ] || git clone -q "https://github.com/nlip-project/$1.git" "vendor/$1"
  git -C "vendor/$1" checkout -q "$2"
  echo "$1 $(git -C vendor/$1 rev-parse HEAD)"
}
pin nlip_sdk b3a6e84
pin nlip_server acdbfc1
pin examples a96488f
[ -d venvs/sdk ] || uv venv -q --python 3.12 venvs/sdk
[ -d venvs/server ] || uv venv -q --python 3.12 venvs/server
VIRTUAL_ENV=venvs/sdk uv pip install -q "pydantic>=2.9.2,<3"
VIRTUAL_ENV=venvs/sdk uv pip install -q --no-deps vendor/nlip_sdk
VIRTUAL_ENV=venvs/server uv pip install -q "fastapi[standard]>=0.115.0,<1" "pydantic>=2.9.2,<3" httpx
VIRTUAL_ENV=venvs/server uv pip install -q --no-deps vendor/nlip_sdk vendor/nlip_server
echo "node: $(node --version) (the TypeScript client is run from source with node's type stripping; nothing is installed)"
