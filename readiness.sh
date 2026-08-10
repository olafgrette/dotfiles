#!/usr/bin/env sh
# Reports which tools referenced across these dotfiles are present on PATH.
# Read-only: never installs or remediates. The set of machines is too varied
# to keep a single install path honest, so this just shows the gaps.

# Replicate fish_add_path from config.fish + darwin.fish so sh sees same bins.
# Without this, bins in ~/.local/bin, ~/.bun/bin etc show as missing when
# readiness.sh runs from sh/zsh (command -v false negatives).
for _d in "$HOME/bin" "$HOME/.local/bin" "$HOME/.bun/bin" "$HOME/.cargo/bin" "$HOME/.opencode/bin" "/opt/homebrew/bin" "/opt/homebrew/sbin" "/usr/local/bin"; do
    case ":$PATH:" in
        *":$_d:"*) ;;
        *) PATH="$_d:$PATH" ;;
    esac
done
export PATH
unset _d

is_gui() {
  [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ] || [ "$(uname -s)" = "Darwin" ]
}

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
if is_gui; then
  check ghostty ghostty
fi
check "tmux" tmux
check "zellij" zellij
check "helix (hx)" hx helix
check git git

group "Install / statusline deps"
check jq jq
check curl curl
check awk awk

group "Helix language servers"
check marksman marksman
check markdown-oxide markdown-oxide
check harper-ls harper-ls

group "Toolchains / version managers"
check uv uv
check cargo cargo
check chruby chruby chruby-exec
check bun bun

group "Agents / AI Tools"
check brunnr brunnr
check claude claude
check gemini gemini
check qmd qmd
check opencode opencode
check "llama-server" llama-server-cuda llama-server

group "Remote / persistence (optional)"
check "et (eternal terminal)" et
check systemd-run systemd-run
check "agy (agent skills)" agy

group "SSH"
check ssh ssh
check ssh-add ssh-add

case "$(uname -s)" in
Linux)
    group "Linux"
    if is_gui; then
      check xdg-open xdg-open
    fi
    check loginctl loginctl
    ;;
Darwin)
    group "macOS"
    check brew brew
    # Font check is best-effort — fc-list may not exist, ghostty itself is the real test
    if command -v fc-list >/dev/null 2>&1; then
        if fc-list | grep -qi "RecMonoCasual"; then
            printf '  \xe2\x9c\x85 %s\n' "RecMonoCasual Nerd Font"
        else
            printf '  \xe2\x9d\x8c %s\n' "RecMonoCasual Nerd Font"
        fi
    else
        # Fallback: check common font install locations
        if ls "$HOME/Library/Fonts/"*RecMonoCasual* >/dev/null 2>&1 || \
           ls /Library/Fonts/*RecMonoCasual* >/dev/null 2>&1; then
            printf '  \xe2\x9c\x85 %s\n' "RecMonoCasual Nerd Font"
        else
            printf '  \xe2\x9d\x8c %s\n' "RecMonoCasual Nerd Font (fc-list not found, checked ~/Library/Fonts)"
        fi
    fi
    ;;
esac

printf '\n'
