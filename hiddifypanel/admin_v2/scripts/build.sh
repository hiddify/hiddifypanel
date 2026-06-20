#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
"$(dirname "$0")/run-with-node.sh" node_modules/vite/bin/vite.js build
