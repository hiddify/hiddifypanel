#!/usr/bin/env bash
set -euo pipefail

resolve_node() {
  if [[ -n "${HIDDIFY_NODE:-}" && -x "${HIDDIFY_NODE}" ]]; then
    echo "${HIDDIFY_NODE}"
    return
  fi
  if command -v node >/dev/null 2>&1; then
    command -v node
    return
  fi
  local cursor_root="${HOME}/.cursor-server/bin/linux-x64"
  if [[ -d "${cursor_root}" ]]; then
    local candidate
    candidate="$(find "${cursor_root}" -maxdepth 2 -name node -type f 2>/dev/null | head -1)"
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      echo "${candidate}"
      return
    fi
  fi
  return 1
}

NODE="$(resolve_node)" || {
  echo "Node.js not found. Install Node/npm or set HIDDIFY_NODE to the node binary." >&2
  exit 1
}

exec "${NODE}" "$@"
