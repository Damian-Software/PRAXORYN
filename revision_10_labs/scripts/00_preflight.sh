#!/usr/bin/env bash
set -uo pipefail
printf '== Local AI preflight (read-only) ==\n'
printf 'OS: '; . /etc/os-release; printf '%s %s\n' "${ID:-unknown}" "${VERSION_ID:-unknown}"
printf 'Kernel: '; uname -r
printf 'Virtualization: '
if grep -qi microsoft /proc/version 2>/dev/null; then echo 'WSL'; else echo 'native/other'; fi
printf 'Memory: '; free -h | sed -n '2p'
printf 'Disk: '; df -h "$HOME" | tail -1
printf 'Systemd: '; if command -v systemctl >/dev/null 2>&1 && test "$(cat /proc/1/comm)" = systemd; then echo yes; else echo no; fi
printf 'GPU diagnostic: '
if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 || true
elif test -x /usr/lib/wsl/lib/nvidia-smi; then /usr/lib/wsl/lib/nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 || true
else echo 'nvidia-smi unavailable: check Windows driver / WSL'; fi
printf 'CUDA compiler: '; if command -v nvcc >/dev/null 2>&1; then nvcc --version | tail -n 1; else echo 'not on PATH'; fi
printf 'Compiler: '; if command -v cmake >/dev/null; then cmake --version | head -1; else echo 'cmake missing'; fi
printf 'No settings were changed.\n'
