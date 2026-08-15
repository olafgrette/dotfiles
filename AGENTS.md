# Dotfiles

Small, path-mirroring dotfiles: repository paths mirror `$HOME`, and `install.sh`
links or renders them into place. Prefer native tool configuration and a few
composable scripts over frameworks, plugin managers, or a dotfile manager.

## Stack
- **Shell**: fish
- **Prompt**: starship
- **Terminal**: ghostty
- **Multiplexer**: zellij (`zmux`); tmux remains available as a fallback (`mux`)
- **Editor**: helix

Tools were chosen for sensible defaults, modern design, and low configuration need — a setup
that works well out of the box without a plugin ecosystem or framework. If a tool needs a lot
of config to be usable, reconsider the tool, not add more config. No stow, no chezmoi, no
dotfile manager.

## Repository model

- Paths under `.config/`, `.local/`, and `.claude/` mirror their destinations in
  `$HOME`.
- Use `symlink` for a whole configuration directory or standalone config at the
  mirrored path. Use `symlink_file` when a directory must remain real so tracked,
  generated, local-only, and tool-managed files can coexist.
- `install.sh` is convergent, but not purely read-only: it backs up conflicting
  destinations, creates links, renders agent directives, installs Starship when
  absent, fetches the configured Ghostty shader, enables Linux linger, and applies
  portable DankMaterialShell settings.
- Generated files, caches, histories, downloaded third-party assets, and runtime
  state do not belong in Git. Check `.gitignore` and the owning tool before adding
  files from a symlinked directory.

## Target machines

- Local macOS (primary)
- Local Linux desktop
- Remote headless Linux machines (SSH only)

Unknown hosts must degrade to safe work/remote defaults. GUI-only setup is guarded
by `DISPLAY`, `WAYLAND_DISPLAY`, or macOS detection.

## Shell configuration and convergence

Fish loads shared configuration from `config.fish`, platform layers from
`conf.d/{darwin,linux}.fish`, and an optional short-hostname layer from
`conf.d/hosts/<host>.fish`. Put a host file in Git only when its contents are safe
and useful on personal machines; work-specific values still belong in local files.

Every interactive shell launches `background-startup` asynchronously. At most once
per five minutes it runs `git pull --ff-only`, then `install.sh` only if the pull
succeeds. It also refreshes skill links and optional local tooling. Keep this path
quiet, bounded, idempotent, and safe to run while other shells are starting. Do not
add prompts or long foreground work.

## Local overrides

**Every tool that supports inclusion or sourcing of a secondary config file must have a
`.local` override wired up**, even without an immediate use case. This is non-negotiable —
driven by work security and IP concerns. Work-specific tooling, credentials, hostnames,
and configurations must never appear in this repo.

Currently implemented:

- Fish: `conf.d/local.fish`
- tmux: `tmux.local.conf`
- Ghostty: `ghostty.local.conf` via optional `config-file`
- DankMaterialShell: `settings.local.json`, merged after the tracked patch
- Agent directives: `UNIVERSAL_AGENT_DIRECTIVES.local.md`, appended during rendering

When adding a tool, wire its `.local` pattern in the same change. Never put actual
proprietary work instructions, credentials, internal hostnames, or work-only tooling
in tracked examples.

## Agent directives

`UNIVERSAL_AGENT_DIRECTIVES.md` is the single source for the agent directive files
installed at `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, and `~/.opencode/AGENTS.md`.
It is tool-neutral on purpose: none of the four destinations is the "real" file that the
others alias, so the source is not named after any of them. `install.sh` generates all
four per-machine rather than symlinking — the repo holds no copy under a vendor path:

- **Scope blocks**: wrap lines in `<!-- scope:personal -->` / `<!-- /scope:personal -->`
  or `<!-- scope:work -->` / `<!-- /scope:work -->` to include them only on the matching
  machine class. Unmarked lines apply everywhere.
- **`personal-hosts`**: one hostname per line — machines listed here render with
  `scope: personal`; every other hostname (including unknown/remote/ephemeral machines)
  renders `scope: work`.
- **`UNIVERSAL_AGENT_DIRECTIVES.local.md`** (gitignored, see above): appended verbatim
  after the rendered directives. This is where actual proprietary work instructions go —
  they never enter git history.

## DankMaterialShell settings

DMS owns a large, writable `~/.config/DankMaterialShell/settings.json`; do not symlink
that file into Git. `.config/DankMaterialShell/settings.patch.json` contains only
portable settings that differ from the installed DMS defaults.

- `dms-settings apply` three-way merges the previously applied patch, live GUI-edited
  settings, and the current tracked/local patches. Local GUI conflicts win.
- `dms-settings capture` regenerates the tracked patch from non-default live settings.
- Display identifiers, usage histories, GPU selection, and other machine/runtime keys
  are blocklisted from capture.
- The ignored `settings.local.json` is the final per-machine overlay. Its top-level
  keys are excluded from shared capture.
- The merge baseline is local state at
  `~/.local/state/DankMaterialShell/dotfiles-settings-baseline.json`.

Capture is explicit; background startup applies repository changes but never writes
back to the repository.

## Agent skills

`skills/` is the tool-neutral source for user-level agent skills. `skill-sync` links
each skill individually into `~/.claude/skills/` and `~/.codex/skills/`, leaving room
for tool-managed or local-only skills. It runs from both `install.sh` and
`background-startup`.

## Validation

- `./readiness.sh`: read-only inventory of expected commands and platform dependencies.
- `bash -n install.sh`: installer syntax.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_dms_settings.py`: DMS merge,
  capture, parser, and atomic-write behavior.
- `git diff --check`: whitespace errors.

Run the smallest relevant checks. Do not run `install.sh` merely as a test: it mutates
the current home directory and may perform network or system setup.

## Key decisions

**No fisher/tide**: starship was chosen because it's shell-agnostic — same config on every
machine, no plugin state to manage or accidentally commit.

**fish_variables not tracked**: mixes runtime state with config and can contain secrets
via `set -U`. Anything worth persisting lives in explicit config files.

**Shaders fetched, not tracked**: third-party GLSL we don't own. Fetching on install
avoids vendoring.

**DMS settings are sparse patches**: the GUI remains the editor, machine state remains
local, and Git records only intentional deviations from upstream defaults.

**hx/helix aliased dynamically**: binary name differs across platforms. `config.fish`
detects whichever exists and aliases the other so EDITOR works everywhere.
