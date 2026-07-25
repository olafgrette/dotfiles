# Dotfiles

Path-mirroring symlinks — repo structure mirrors `$HOME`, `install.sh` links it all in.
Use `symlink` for directories, `symlink_file` for individual files.

## Stack
- **Shell**: fish
- **Prompt**: starship
- **Terminal**: ghostty
- **Multiplexers**: tmux (`mux`), zellij (`zmux`)
- **Editor**: helix

Tools were chosen for sensible defaults, modern design, and low configuration need — a setup
that works well out of the box without a plugin ecosystem or framework. If a tool needs a lot
of config to be usable, reconsider the tool, not add more config. No stow, no chezmoi, no
dotfile manager — `install.sh` is a short bash file that symlinks, renders agent directives
per-host, and handles one-time setup (starship install, shader fetch, linger).

## Target machines
- Local macOS (primary)
- Local Linux desktop
- Remote headless Linux machines (SSH only)

## Local overrides

**Every tool that supports inclusion or sourcing of a secondary config file must have a
`.local` override wired up**, even without an immediate use case. This is non-negotiable —
driven by work security and IP concerns. Work-specific tooling, credentials, hostnames,
and configurations must never appear in this repo.

Currently implemented: `conf.d/local.fish`, `tmux.local.conf`, `ghostty.local.conf`
(via `config-file = ?ghostty.local.conf`), `UNIVERSAL_AGENT_DIRECTIVES.local.md` (appended
in `render_agent_directives`). When adding a new tool, setting up the `.local` pattern
is part of the work, not a follow-up.

## Agent directives

`UNIVERSAL_AGENT_DIRECTIVES.md` is the single source for the agent directive files
installed at `~/.claude/CLAUDE.md`, `~/.gemini/GEMINI.md`, and `~/.opencode/AGENTS.md`.
It is tool-neutral on purpose: none of the three destinations is the "real" file that the
others alias, so the source is not named after any of them. `install.sh` generates all
three per-machine rather than symlinking — the repo holds no copy under a vendor path:

- **Scope blocks**: wrap lines in `<!-- scope:personal -->` / `<!-- /scope:personal -->`
  or `<!-- scope:work -->` / `<!-- /scope:work -->` to include them only on the matching
  machine class. Unmarked lines apply everywhere.
- **`personal-hosts`**: one hostname per line — machines listed here render with
  `scope: personal`; every other hostname (including unknown/remote/ephemeral machines)
  renders `scope: work`.
- **`UNIVERSAL_AGENT_DIRECTIVES.local.md`** (gitignored, see above): appended verbatim
  after the rendered directives. This is where actual proprietary work instructions go —
  they never enter git history.

## Room coordination

Room ID: **`dotfiles`**. Agents use their git branch name as username (`main` for work
directly on main); the human is `olaf`.

Every `room` command needs `--token`. Register once with `room join <username>` — the
token lands in `~/.room/state/room-<username>.token` and is global, so read it from there
rather than passing it around. Then `room subscribe dotfiles --token <token>` to receive
messages.

Commands only work against a running daemon: `room daemon --persistent --room dotfiles`.
It is not started at login — start it manually when coordinating, or skip the room
entirely for solo sessions. Nothing in this repo depends on it.

## Key decisions

**No fisher/tide**: starship was chosen because it's shell-agnostic — same config on every
machine, no plugin state to manage or accidentally commit.

**fish_variables not tracked**: mixes runtime state with config and can contain secrets
via `set -U`. Anything worth persisting lives in explicit config files.

**Shaders fetched, not tracked**: third-party GLSL we don't own. Fetching on install
avoids vendoring.

**hx/helix aliased dynamically**: binary name differs across platforms. `config.fish`
detects whichever exists and aliases the other so EDITOR works everywhere.
