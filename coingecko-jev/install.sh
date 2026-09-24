#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python typesafe-sdk requests truststore fastapi "uvicorn[standard]" websockets pytest
echo "Installed. Test with: ./start.sh"
