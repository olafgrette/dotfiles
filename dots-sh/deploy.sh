#!/usr/bin/env bash
# Deploy the dots.oag.sh static assets.
#
# wrangler is fetched by npx and never installed: this repository is shell and
# Python, and one Worker does not justify a node_modules. The major version is
# pinned so a wrangler 5 release cannot change what deploy does without an
# explicit edit here.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

WRANGLER=(npx --yes wrangler@4)

usage() {
    cat >&2 <<'EOF'
usage: deploy.sh {deploy|check|verify}

  deploy   stage, publish, and verify static assets (requires Wrangler login)
  check    build without publishing
  verify   verify the live bootstrap and every retained asset hash
EOF
    exit 2
}

case "${1-deploy}" in
    deploy) python3 artifacts.py stage; "${WRANGLER[@]}" deploy; python3 artifacts.py verify ;;
    check)  python3 artifacts.py stage; "${WRANGLER[@]}" deploy --dry-run ;;
    verify) python3 artifacts.py verify ;;
    *)      usage ;;
esac
