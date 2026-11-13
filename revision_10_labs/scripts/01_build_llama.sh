#!/usr/bin/env bash
set -euo pipefail
ROOT="${LOCALAI_BUILD_ROOT:-$HOME/src/llama.cpp}"
BACKEND="${LOCALAI_BACKEND:-cuda}"
case "$BACKEND" in cuda|cpu) ;; *) echo 'LOCALAI_BACKEND must be cuda or cpu' >&2; exit 2;; esac
for cmd in git cmake c++; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 2; }; done
if [[ "$BACKEND" = cuda ]] && ! command -v nvcc >/dev/null; then
  echo 'CUDA compiler missing. Install toolkit only; not a Linux GPU driver in WSL.' >&2; exit 2
fi
mkdir -p "$(dirname "$ROOT")"
if [[ ! -e "$ROOT/.git" ]]; then
  git clone https://github.com/ggml-org/llama.cpp.git "$ROOT"
fi
cd "$ROOT"
if [[ -n "${LOCALAI_REF:-}" ]]; then git checkout "${LOCALAI_REF}"; fi
printf 'Build commit: '; git rev-parse HEAD
if [[ "$BACKEND" = cuda ]]; then cmake -S . -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
else cmake -S . -B build -DGGML_CUDA=OFF -DCMAKE_BUILD_TYPE=Release; fi
cmake --build build --config Release -j "${LOCALAI_JOBS:-4}" --target llama-server
./build/bin/llama-server --help | head -n 4 || true
printf 'Record this commit in the deployment manifest: '; git rev-parse HEAD
