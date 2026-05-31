#!/usr/bin/env sh
# Reports which tools referenced across these dotfiles are present on PATH.
# Read-only: never installs or remediates. The set of machines is too varied
# to keep a single install path honest, so this just shows the gaps.

check() {
    # $1 = display name, $2... = candidate binaries (present if ANY exist)
    name="$1"
    shift
    for bin in "$@"; do
        if command -v "$bin" >/dev/null 2>&1; then
            printf '  \xe2\x9c\x85 %s\n' "$name"
            return
        fi
    done
    printf '  \xe2\x9d\x8c %s\n' "$name"
}

group() {
    printf '\n%s\n' "$1"
}

group "Core stack"
check fish fish
check starship starship
check ghostty ghostty
check tmux tmux
check "helix (hx)" hx helix
check git git

group "Install / statusline deps"
check jq jq
check curl curl
check bc bc

group "Helix language servers"
check marksman marksman
check markdown-oxide markdown-oxide
check harper-ls harper-ls

group "Toolchains / version managers"
check uv uv
check cargo cargo
check chruby chruby chruby-exec
check bun bun

group "Agents"
check claude claude
check gemini gemini

group "SSH"
check ssh ssh
check ssh-add ssh-add

case "$(uname -s)" in
Linux)
    group "Linux desktop (Hyprland)"
    check hyprctl hyprctl
    check start-hyprland start-hyprland
    check xdg-open xdg-open
    ;;
Darwin)
    group "macOS"
    check brew brew
    ;;
esac

printf '\n'
