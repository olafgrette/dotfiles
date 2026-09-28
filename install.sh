#!/usr/bin/env bash
set -e

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1-}" in
    '') BACKGROUND=0 ;;
    --background) BACKGROUND=1 ;;
    *) echo 'usage: install.sh [--background]' >&2; exit 2 ;;
esac
if [ "${DOTFILES_INSTALL_LOCKED-}" != "$DOTFILES" ]; then
    exec python3 "$DOTFILES/.local/bin/dotfiles-update" --install "$@"
fi

is_gui() {
  [[ -n "$DISPLAY" || -n "$WAYLAND_DISPLAY" || "$(uname -s)" == "Darwin" ]]
}

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

# Strip domain/FQDN — personal-hosts contains short names (olafmbp, lightshow),
# but uname -n can return olafmbp.local / FQDN on macOS/DHCP.
short_host() {
    local host
    host="$(hostname -s 2>/dev/null || uname -n)"
    printf '%s' "${host%%.*}"
}

is_personal() {
    [ -f "$DOTFILES/personal-hosts" ] && grep -qxF "$(short_host)" "$DOTFILES/personal-hosts"
}

# Render UNIVERSAL_AGENT_DIRECTIVES.md into the agent directives shared by all
# three tools, filtering <!-- scope:personal/work --> blocks by hostname and
# appending the gitignored local override (work-only content that must
# never enter git history).
render_agent_directives() {
    local scope="work"
    if is_personal; then
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
# Older installs linked the entire library directory. Keep a recovery link
# until every local entry has moved, so an interrupted migration can resume.
LIB_DIR="$HOME/.local/lib"
LIB_RECOVERY="$HOME/.local/lib.dotfiles-link"
if [ -L "$LIB_DIR" ] && [ "$LIB_DIR" -ef "$DOTFILES/.local/lib" ]; then
    if [ -e "$LIB_RECOVERY" ] || [ -L "$LIB_RECOVERY" ]; then
        echo "Cannot migrate $LIB_DIR: $LIB_RECOVERY already exists" >&2
        exit 1
    fi
    mv "$LIB_DIR" "$LIB_RECOVERY"
fi
if [ -L "$LIB_RECOVERY" ] && [ "$LIB_RECOVERY" -ef "$DOTFILES/.local/lib" ]; then
    mkdir -p "$LIB_DIR"
    (
        shopt -s dotglob nullglob
        for entry in "$DOTFILES/.local/lib/"*; do
            # This is the only library file owned by the repository.
            [ "${entry##*/}" = llama-common.sh ] && continue
            target="$LIB_DIR/${entry##*/}"
            if [ -e "$target" ] || [ -L "$target" ]; then
                echo "Library migration conflict: $target; both copies preserved" >&2
                exit 1
            fi
            mv "$entry" "$target"
        done
    )
    rm "$LIB_RECOVERY"
fi
symlink_file .local/lib/llama-common.sh
symlink_file .local/bin/gemma-serve
symlink_file .local/bin/muse-glimmer-serve
symlink_file .local/bin/qwen-fast-serve
symlink_file .local/bin/qwen-precise-serve
symlink_file .local/bin/dms-settings
symlink_file .local/bin/private-sync
symlink_file .local/bin/dotfiles-update
symlink_file .claude/statusline-command.sh

# DMS 1.6 writes sparse settings. Merge shared preferences while keeping GUI
# edits and machine-specific settings local.
if [ "$(uname -s)" = "Linux" ] && is_gui && [ -f "$HOME/.config/DankMaterialShell/.firstlaunch" ]; then
    # dms-shell owns the unit. DMS setup enables it, and convergence restores
    # that package-owned service link if local state removes it later.
    mkdir -p "$HOME/.config/systemd/user/graphical-session.target.wants"
    ln -sfn /usr/lib/systemd/user/dms.service \
        "$HOME/.config/systemd/user/graphical-session.target.wants/dms.service"

    # This DMS fragment contains only user keybind overrides, so let its GUI
    # write directly to the tracked file. Do not create Hyprland config on a
    # DMS setup using another compositor.
    if [ -f "$HOME/.config/hypr/dms/binds-user.lua" ] || [ -L "$HOME/.config/hypr/dms/binds-user.lua" ]; then
        symlink_file .config/hypr/dms/binds-user.lua
        # Lua helper those overrides require(). Linked as a single file because
        # the rest of ~/.config/hypr is DMS-generated state, not configuration.
        symlink_file .config/hypr/monitor-dir.lua
    fi
    "$DOTFILES/.local/bin/dms-settings" apply
fi

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
generate_file .codex/AGENTS.md "$AGENT_DIRECTIVES"

# Linux: let user processes (tmux/zellij sessions) survive SSH logout.
# systemd-logind otherwise reaps them on disconnect. enable-linger is the
# rootless alternative to KillUserProcesses=no in logind.conf.
# Non-fatal: containers/WSL often have the loginctl binary without a running
# systemd/dbus, which would otherwise abort the whole install under set -e.
if [ "$BACKGROUND" = 0 ] && [ "$(uname -s)" = "Linux" ] && command -v loginctl &>/dev/null; then
    CURRENT_USER="$(id -un)"
    if [ "$(loginctl show-user "$CURRENT_USER" -p Linger --value 2>/dev/null)" != "yes" ]; then
        echo "Enabling user lingering for $CURRENT_USER"
        loginctl enable-linger "$CURRENT_USER" || echo "Warning: could not enable linger (no systemd/dbus?)"
    fi
fi

# Avoid user startup hooks while installing, including agent prompts.
fish --no-config -c 'source $argv[1]; skill-sync' "$DOTFILES/.config/fish/functions/skill-sync.fish"

if [ "$BACKGROUND" = 0 ] && ! command -v starship &>/dev/null; then
    echo "Installing starship..."
    curl -sS https://starship.rs/install.sh | sh -s -- -y
fi

# Download zellij plugins (gitignored, fetched on install). The path stays
# fixed for config.kdl; a stamp records the fetched version so a bump here
# replaces the file on the next run.
ZELLIJ_PLUGINS_DIR="$HOME/.config/zellij/plugins"
CHOOSE_TREE_VERSION="v0.4.2"
CHOOSE_TREE_WASM="$ZELLIJ_PLUGINS_DIR/zellij-choose-tree.wasm"
if [ "$BACKGROUND" = 0 ] && { [ ! -f "$CHOOSE_TREE_WASM" ] || [ "$(cat "$CHOOSE_TREE_WASM.version" 2>/dev/null)" != "$CHOOSE_TREE_VERSION" ]; }; then
    echo "Downloading zellij plugin: zellij-choose-tree $CHOOSE_TREE_VERSION"
    mkdir -p "$ZELLIJ_PLUGINS_DIR"
    curl -sfL "https://github.com/laperlej/zellij-choose-tree/releases/download/$CHOOSE_TREE_VERSION/zellij-choose-tree.wasm" \
        -o "$CHOOSE_TREE_WASM.part" \
        && mv "$CHOOSE_TREE_WASM.part" "$CHOOSE_TREE_WASM" \
        && echo "$CHOOSE_TREE_VERSION" > "$CHOOSE_TREE_WASM.version"
fi

# Download ghostty shaders (gitignored, fetched on install)
if [ "$BACKGROUND" = 0 ] && is_gui; then
SHADERS_DIR="$HOME/.config/ghostty/shaders"
SHADERS_BASE="https://raw.githubusercontent.com/KroneCorylus/ghostty-shader-playground/main/public/shaders"
mkdir -p "$SHADERS_DIR"
for shader in cursor_frozen.glsl; do
    if [ ! -f "$SHADERS_DIR/$shader" ]; then
        echo "Downloading shader: $shader"
        curl -sfL "$SHADERS_BASE/$shader" -o "$SHADERS_DIR/$shader"
    fi
done
fi
