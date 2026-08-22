#!/usr/bin/env bash
# Foreground entry point for the Arch system layer.
#
# install.sh converges HOME everywhere. This wrapper keeps aconfmgr off work,
# remote, and unknown hosts; adds rollback before system mutation; and realizes
# the small amount of state that aconfmgr writes but cannot activate itself.
set -e
set -o pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACONFMGR_CONFIG="$REPO/aconfmgr"
SHADOW_UNIT="/etc/systemd/system/grub-btrfsd.service"

die() {
    echo "aconf: $*" >&2
    exit 2
}

usage() {
    cat >&2 <<'EOF'
usage: aconf.sh {lint|diff|save|apply}

  lint   syntax-check and lint the aconfmgr configuration
  diff   show managed-file drift; packages are not included
  save   capture inverse system drift to 99-unsorted.sh for review
  apply  snapshot, then interactively converge the system with aconfmgr

Apply is foreground-only, defaults to refusal, and makes no automatic rollback.
EOF
    exit 2
}

short_host() {
    local host
    host="$(hostname -s 2>/dev/null || uname -n)"
    echo "${host%%.*}"
}

require_declared_arch_host() {
    [ -r /etc/os-release ] || die "cannot read /etc/os-release"
    [ "$(. /etc/os-release && printf '%s' "${ID:-}")" = arch ] ||
        die "system layer is Arch-only; this host is not Arch"
    grep -qxF "$(short_host)" "$REPO/personal-hosts" 2>/dev/null ||
        die "$(short_host) is not in personal-hosts; refusing the system layer"
    [ -d "$ACONFMGR_CONFIG" ] || die "missing $ACONFMGR_CONFIG"
}

require_commands() {
    local missing=() command
    for command in "$@"; do
        command -v "$command" &>/dev/null || missing+=("$command")
    done
    [ ${#missing[@]} -eq 0 ] || die "missing prerequisites: ${missing[*]}"
}

run_aconfmgr() {
    aconfmgr --config "$ACONFMGR_CONFIG" --aur-helper yay --color never "$@"
}

gate() {
    require_declared_arch_host
    require_commands aconfmgr yay
}

confirm_apply() {
    local host="$1" reply
    printf 'Create a Timeshift snapshot and apply system configuration on %s? [y/N] ' \
        "$host" >&2
    IFS= read -r reply || die "confirmation input closed"
    [[ "$reply" == y || "$reply" == Y ]] || die "confirmation refused"
}

create_rollback_snapshot() {
    local host="$1" comment
    comment="pre-aconfmgr-$host-$(date -u +%Y%m%dT%H%M%SZ)"
    if ! sudo timeshift --create --btrfs --comments "$comment" --tags O --scripted; then
        die "Timeshift snapshot failed; refusing apply"
    fi
    printf 'aconf: created Timeshift snapshot %s\n' "$comment"
}

apply_system() {
    local host
    [ -t 0 ] && [ -t 1 ] || die "apply requires an interactive terminal"
    require_commands sudo timeshift date locale-gen systemctl
    if [ -e "$SHADOW_UNIT" ] || [ -L "$SHADOW_UNIT" ]; then
        die "$SHADOW_UNIT reappeared; inspect it and remove it explicitly before apply"
    fi

    host="$(short_host)"
    confirm_apply "$host"
    create_rollback_snapshot "$host"
    run_aconfmgr --paranoid apply

    sudo locale-gen
    sudo systemctl daemon-reload
    if systemctl list-unit-files greetd.service &>/dev/null; then
        systemctl is-enabled --quiet greetd.service ||
            die "greetd is installed but not enabled"
    fi
}

# Optional machine-local profile hook, never shared. It may adjust wrapper
# variables or functions without exposing private host details in this repo.
if [ -f "$REPO/aconf.local.sh" ]; then
    . "$REPO/aconf.local.sh"
fi

case "${1-}" in
    lint)
        gate
        run_aconfmgr check
        ;;
    diff)
        gate
        run_aconfmgr diff /
        ;;
    save)
        gate
        run_aconfmgr save
        ;;
    apply)
        gate
        apply_system
        ;;
    *)
        usage
        ;;
esac
