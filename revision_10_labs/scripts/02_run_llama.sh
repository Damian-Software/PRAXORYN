#!/usr/bin/env bash
set -euo pipefail
MODEL_PATH="${LOCALAI_MODEL:?Set LOCALAI_MODEL to an existing, licensed GGUF file}"
ROOT="${LOCALAI_BUILD_ROOT:-$HOME/src/llama.cpp}"
BINARY="$ROOT/build/bin/llama-server"
[[ -f "$MODEL_PATH" ]] || { echo 'Model file not found' >&2; exit 2; }
[[ -x "$BINARY" ]] || { echo 'llama-server missing. Run 01_build_llama.sh' >&2; exit 2; }
KEY_DIR="$HOME/.config/localai"; KEY_FILE="$KEY_DIR/api_keys.txt"
umask 077; mkdir -p "$KEY_DIR"
if [[ ! -s "$KEY_FILE" ]]; then
  python3 -c 'import secrets; print(secrets.token_urlsafe(36))' > "$KEY_FILE"
fi
chmod 600 "$KEY_FILE"
echo 'Listening only on 127.0.0.1:8081. API key remains in a private file.'
exec "$BINARY" --model "$MODEL_PATH" --alias local-chat \
  --host 127.0.0.1 --port 8081 --ctx-size 4096 \
  --n-gpu-layers "${LOCALAI_GPU_LAYERS:-99}" --api-key-file "$KEY_FILE"
