#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
bash scripts/build.sh
echo "Admin v2 built to hiddifypanel/static/admin-v2/"
