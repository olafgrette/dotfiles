#!/usr/bin/env bash
set -e

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

symlink() {
    local src="$DOTFILES/$1"
    local dst="$HOME/$1"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        echo "Backing up existing $dst -> ${dst}.bak"
        mv "$dst" "${dst}.bak"
    fi
    ln -sfn "$src" "$dst"
    echo "Linked $dst"
}

symlink_file() {
    local src="$DOTFILES/$1"
    local dst="$HOME/$1"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        echo "Backing up existing $dst -> ${dst}.bak"
        mv "$dst" "${dst}.bak"
    fi
    ln -sf "$src" "$dst"
    echo "Linked $dst"
}

# Render UNIVERSAL_AGENT_DIRECTIVES.md into the agent directives shared by all
# three tools, filtering <!-- scope:personal/work --> blocks by hostname and
# appending the gitignored local override (work-only content that must
# never enter git history).
render_agent_directives() {
    # Strip domain/FQDN — personal-hosts contains short names (olafmbp, lightshow),
    # but uname -n can return olafmbp.local / FQDN on macOS/DHCP.
    local host
    host="$(hostname -s 2>/dev/null || uname -n)"
    host="${host%%.*}"
    local scope="work"
    if [ -f "$DOTFILES/personal-hosts" ] && \
       grep -qxF "$host" "$DOTFILES/personal-hosts"; then
        scope="personal"
    fi

    local rendered
    rendered="$(awk -v scope="$scope" '
        /^<!-- scope:[a-z]+ -->$/ {
            tag = $0; gsub(/<!-- scope:|-->/, "", tag); gsub(/ /, "", tag)
            skip = (tag != scope); next
        }
        /^<!-- \/scope:[a-z]+ -->$/ { skip = 0; next }
        !skip
    ' "$DOTFILES/UNIVERSAL_AGENT_DIRECTIVES.md")"

    if [ -f "$DOTFILES/UNIVERSAL_AGENT_DIRECTIVES.local.md" ]; then
        rendered="$rendered"$'\n\n'"$(cat "$DOTFILES/UNIVERSAL_AGENT_DIRECTIVES.local.md")"
    fi

    printf '%s\n' "$rendered"
}

generate_file() {
    local dst="$HOME/$1"
    local content="$2"
    mkdir -p "$(dirname "$dst")"
    rm -f "$dst"
    printf '%s\n' "$content" > "$dst"
    echo "Generated $dst"
}

symlink .config/fish
symlink .config/ghostty
symlink .config/helix
symlink .config/starship.toml
symlink .config/tmux
symlink .config/zellij
symlink .local/lib
symlink_file .local/bin/gemma-serve
symlink_file .local/bin/qwen-fast-serve
symlink_file .local/bin/qwen-precise-serve
symlink_file .claude/statusline-command.sh

# Add statusline config to ~/.claude/settings.json if not already present
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [ ! -f "$CLAUDE_SETTINGS" ]; then
    echo '{}' > "$CLAUDE_SETTINGS"
fi
if ! jq -e '.statusLine' "$CLAUDE_SETTINGS" > /dev/null 2>&1; then
    tmp=$(mktemp)
    jq '.statusLine = {"type": "command", "command": "bash ~/.claude/statusline-command.sh"}' "$CLAUDE_SETTINGS" > "$tmp"
    mv "$tmp" "$CLAUDE_SETTINGS"
    echo "Added statusLine to $CLAUDE_SETTINGS"
fi
AGENT_DIRECTIVES="$(render_agent_directives)"
generate_file .claude/CLAUDE.md "$AGENT_DIRECTIVES"
generate_file .gemini/GEMINI.md "$AGENT_DIRECTIVES"
generate_file .opencode/AGENTS.md "$AGENT_DIRECTIVES"

# Linux: let user processes (tmux/zellij sessions) survive SSH logout.
# systemd-logind otherwise reaps them on disconnect. enable-linger is the
# rootless alternative to KillUserProcesses=no in logind.conf.
# Non-fatal: containers/WSL often have the loginctl binary without a running
# systemd/dbus, which would otherwise abort the whole install under set -e.
if [ "$(uname -s)" = "Linux" ] && command -v loginctl &>/dev/null; then
    CURRENT_USER="$(id -un)"
    if [ "$(loginctl show-user "$CURRENT_USER" -p Linger --value 2>/dev/null)" != "yes" ]; then
        echo "Enabling user lingering for $CURRENT_USER"
        loginctl enable-linger "$CURRENT_USER" || echo "Warning: could not enable linger (no systemd/dbus?)"
    fi
fi

# Sync Claude skills (also run by background-startup on each shell start)
fish -c claude-skill-sync

if ! command -v starship &>/dev/null; then
    echo "Installing starship..."
    curl -sS https://starship.rs/install.sh | sh -s -- -y
fi

# Download ghostty shaders (gitignored, fetched on install)
SHADERS_DIR="$HOME/.config/ghostty/shaders"
SHADERS_BASE="https://raw.githubusercontent.com/KroneCorylus/ghostty-shader-playground/main/public/shaders"
mkdir -p "$SHADERS_DIR"
for shader in cursor_frozen.glsl; do
    if [ ! -f "$SHADERS_DIR/$shader" ]; then
        echo "Downloading shader: $shader"
        curl -sfL "$SHADERS_BASE/$shader" -o "$SHADERS_DIR/$shader"
    fi
done
