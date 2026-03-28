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

symlink .config/fish
symlink .config/ghostty
symlink .config/helix
symlink .config/starship.toml
symlink .config/tmux

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
        curl -sL "$SHADERS_BASE/$shader" -o "$SHADERS_DIR/$shader"
    fi
done
