#!/bin/sh
# curl pipes the script on stdin; reopen the terminal for confirmations.
{
[ -t 0 ] || {
    if ! (: </dev/tty) 2>/dev/null; then
        echo "init: no controlling terminal; run init.sh from an interactive terminal" >&2
        exit 2
    fi
    exec </dev/tty
}
set -eu

REPO_URL=https://github.com/olafgrette/dotfiles.git
REPO="$HOME/dotfiles"
OS_RELEASE=/etc/os-release

die() {
    echo "init: $*" >&2
    exit 2
}

short_host() {
    host=$(hostname -s 2>/dev/null || uname -n)
    printf '%s\n' "${host%%.*}"
}

distro_id() {
    [ -r "$OS_RELEASE" ] || return 0
    (
        # shellcheck disable=SC1090
        . "$OS_RELEASE"
        printf '%s\n' "${ID:-}"
    )
}

[ "$(id -u)" -ne 0 ] || die "refusing to run as root; run init.sh as your user"

HOST=$(short_host)
if [ "$HOST" = archlinux ]; then
    die "hostname is still 'archlinux'; set it first: sudo hostnamectl set-hostname <hostname>"
fi

ARCH=0
if [ "$(distro_id)" = arch ]; then
    ARCH=1
fi

if [ ! -e "$REPO" ]; then
    command -v git >/dev/null 2>&1 ||
        die "missing prerequisite: git; install it with: sudo pacman -S --needed git"
    git clone "$REPO_URL" "$REPO"
else
    echo "Leaving existing $REPO unchanged."
fi

cat <<EOF
To use SSH for future Git operations, run:
  git -C $REPO remote set-url origin git@github.com:olafgrette/dotfiles.git
EOF

[ -f "$REPO/install.sh" ] || die "$REPO exists but has no install.sh"
[ -f "$REPO/personal-hosts" ] || die "$REPO exists but has no personal-hosts"

PERSONAL_ARCH=0
if [ "$ARCH" -eq 1 ] && grep -qxF "$HOST" "$REPO/personal-hosts"; then
    PERSONAL_ARCH=1
fi

if [ "$PERSONAL_ARCH" -eq 1 ]; then
    [ -f "$REPO/aconf.sh" ] || die "$REPO exists but has no aconf.sh"
    (cd "$REPO" && ./aconf.sh apply)
    if [ ! -d "$HOME/.config/hypr" ]; then
        GHOSTTY="$HOME/.config/ghostty"
        REPO_GHOSTTY="$REPO/.config/ghostty"
        if [ -L "$GHOSTTY" ] && [ "$GHOSTTY" -ef "$REPO_GHOSTTY" ]; then
            die "Hyprland configuration is absent, but Ghostty is linked into the repo; move that link aside and run dms setup manually"
        fi
        command -v dms >/dev/null 2>&1 ||
            die "missing prerequisite: dms; aconf.sh apply should install dms-shell"
        dms setup || die "dms setup failed or was aborted"
        [ -d "$HOME/.config/hypr" ] ||
            die "dms setup completed without creating a Hyprland configuration"
    fi
fi

(cd "$REPO" && ./install.sh)

cat <<EOF
Initialization complete. Verify with:
  $REPO/readiness.sh
EOF
exit 0
}
