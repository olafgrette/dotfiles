# Dotfiles

Path-mirroring symlinks — repo structure mirrors `$HOME`, `install.sh` links it all in.
Use `symlink` for directories, `symlink_file` for individual files.

## Stack
- **Shell**: fish
- **Prompt**: starship
- **Terminal**: ghostty
- **Multiplexer**: tmux
- **Editor**: helix

Tools were chosen for sensible defaults, modern design, and low configuration need — a setup
that works well out of the box without a plugin ecosystem or framework. If a tool needs a lot
of config to be usable, reconsider the tool, not add more config. No stow, no chezmoi, no
dotfile manager — the install script is 50 lines of bash and that's the point.

## Target machines
- Local macOS (primary)
- Local Linux desktop (Hyprland)
- Remote headless Linux machines (SSH only)

## Local overrides

**Every tool that supports inclusion or sourcing of a secondary config file must have a
`.local` override wired up**, even without an immediate use case. This is non-negotiable —
driven by work security and IP concerns. Work-specific tooling, credentials, hostnames,
and configurations must never appear in this repo.

Currently implemented: `conf.d/local.fish`, `tmux.local.conf`. When adding a new tool,
setting up the `.local` pattern is part of the work, not a follow-up.

## Key decisions

**No fisher/tide**: starship was chosen because it's shell-agnostic — same config on every
machine, no plugin state to manage or accidentally commit.

**fish_variables not tracked**: mixes runtime state with config and can contain secrets
via `set -U`. Anything worth persisting lives in explicit config files.

**Shaders fetched, not tracked**: third-party GLSL we don't own. Fetching on install
avoids vendoring.

**hx/helix aliased dynamically**: binary name differs across platforms. `config.fish`
detects whichever exists and aliases the other so EDITOR works everywhere.
