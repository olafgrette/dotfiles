#!/usr/bin/env bash
# Deploy the dots.oag.sh Worker.
#
# wrangler is fetched by npx and never installed: this repository is shell and
# Python, and one Worker does not justify a node_modules. The major version is
# pinned so a wrangler 5 release cannot change what deploy does without an
# explicit edit here.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

WRANGLER=(npx --yes wrangler@4)
URL=https://dots.oag.sh

usage() {
    cat >&2 <<'EOF'
usage: deploy.sh {deploy|check|verify|tail}

  deploy   build and publish the Worker (asks for login on first run)
  check    build without publishing
  verify   fetch the live URL and confirm it serves init.sh
  tail     stream live logs
EOF
    exit 2
}

verify() {
    # Compare against the source of truth rather than just checking for a 200:
    # a stale or wrong-origin response would still return 200.
    local served expected
    served=$(curl -fsSL --max-time 15 "$URL") ||
        { echo "verify: $URL did not serve a script" >&2; return 1; }
    expected=$(curl -fsSL --max-time 15 \
        https://raw.githubusercontent.com/olafgrette/dotfiles/main/init.sh) ||
        { echo "verify: could not read init.sh from GitHub to compare" >&2; return 1; }

    if [ "$served" = "$expected" ]; then
        printf 'verify: %s serves init.sh (%s bytes)\n' "$URL" "${#served}"
    else
        echo "verify: $URL served something other than init.sh" >&2
        return 1
    fi
}

case "${1-deploy}" in
    deploy) "${WRANGLER[@]}" deploy ;;
    check)  "${WRANGLER[@]}" deploy --dry-run --outdir "$(mktemp -d)" ;;
    verify) verify ;;
    tail)   "${WRANGLER[@]}" tail ;;
    *)      usage ;;
esac
