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

`zmux` clears an exited saved session if resurrection fails, then retries once
under the same name. This discards that session's saved layout and scrollback.
It never forces deletion of a running session.

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
- `~/.local/lib` stays real; only `llama-common.sh` is linked. Installation
  migrates the old whole-directory link and its local packages, retaining a
  `lib.dotfiles-link` recovery marker until the move completes. Existing
  `lib.bak` backups remain untouched; conflicting entries stop migration.
- `install.sh` backs up conflicting destinations, creates links, renders agent
  directives, applies portable Dux Shell settings, installs missing
  Starship, fetches the Ghostty shader and zellij plugins, installs the Brood War
  cursor theme on Linux GUI hosts without selecting it, and enables Linux linger.
  `install.sh --background` skips network setup and linger changes.
- Generated files, caches, histories, downloaded third-party assets, and runtime
  state do not belong in Git. Check `.gitignore` and the owning tool before adding
  files from a symlinked directory.
- `aconfmgr/` is the exception: system-layer declarations, deliberately top-level
  and never linked into `$HOME`. Everything under `.config/` means "linked into
  `~/.config`"; the system layer is not that.

## Target machines

- Local macOS (primary)
- Local Linux desktop
- Remote headless Linux machines (SSH only)

Unknown hosts must degrade to safe work/remote defaults. GUI-only setup is guarded
by `DISPLAY`, `WAYLAND_DISPLAY`, or macOS detection.

## Arch system layer

`install.sh` converges `$HOME` on every host. `aconf.sh` converges the Arch
system layer — explicit packages, reviewed `/etc`, unit enablement — and only on
hosts listed in `personal-hosts`; work, remote, unknown, and non-Arch hosts are
refused before anything inspects the system. `init.sh` is the once-per-box entry
point. Setup instructions live in `init.md`.

- The repository is public, so `aconfmgr/99-scope.sh` derives the `/etc`
  allowlist from registered declarations and ignores everything else. Declaring
  a path is what admits it; there is no denylist to update. Firewall, SSH,
  VPN, tunnel, and network configuration stay out, along with their contents.
- Common intent is `20-packages.sh` and `30-system.sh`. A `hosts/<short-name>`
  overlay carries only what would be wrong on another machine, which in practice
  means CPU and GPU hardware. A declared host with no overlay warns and
  converges against common intent alone.
- Anything added to `install.sh` runs on work and remote machines too. Personal-
  only additions need an explicit `is_personal` gate; the failure is silent.
- Nothing starts or restarts services. `apply` takes a Timeshift snapshot first
  and confirms with a default of no.
- After the snapshot, `apply` bootstraps the signed OpenAI repository and
  `chatgpt-bin` with the official installer when the repository, sync database,
  or package is missing. This performs a full system upgrade. Repository config
  is tracked; signing-key trust stays machine-local.

## Shell configuration and convergence

Fish loads platform and host snippets before `config.fish`, which loads shared
defaults and then `local.fish` last. A startup migration moves the old
`conf.d/local.fish` before it can be sourced; if both paths exist, it reports the
conflict and preserves both. Put a host file in Git only when its contents are
safe and useful on personal machines; work-specific values belong in local files.

Every interactive shell launches `background-startup` asynchronously after local
configuration has loaded. Its Python supervisor, `dotfiles-update`, shares a
nonblocking lock with foreground installs.
At most once per five minutes it pulls clean `main` tracking `origin/main`, then
applies only changed HOME inputs with `install.sh --background`. Failed applies
retain their receipt for retry.
The entire background run, including optional local tooling, has a 120-second
limit. State and the last failure log live in `$XDG_STATE_HOME/dotfiles` (default
`~/.local/state/dotfiles`). Keep this path quiet and free of prompts.

## Local overrides

**Every tool that supports inclusion or sourcing of a secondary config file must have a
`.local` override wired up**, even without an immediate use case. This is non-negotiable —
driven by work security and IP concerns. Work-specific tooling, credentials, hostnames,
and configurations must never appear in this repo.

Currently implemented:

- Fish: `local.fish`, sourced last by `config.fish`
- tmux: `tmux.local.conf`
- Ghostty: `ghostty.local.conf` via optional `config-file`
- Dux Shell: `settings.local.json`, merged after the tracked patch
- Agent directives: `UNIVERSAL_AGENT_DIRECTIVES.local.md`, appended during rendering
- `aconf.sh`: `aconf.local.sh`, sourced before dispatch
- aconfmgr: `aconfmgr/aconfmgr.local`, for temporary or experimental packages

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

## Dux Shell settings

Dux Shell 2.0 owns writable `~/.config/dms/settings.json` and native `config.d/`
drop-ins. Do not symlink these live JSON files into Git: GUI writes can include
machine fields. `.config/dms/settings.patch.json` holds captured portable intent.

- `dms-settings apply` publishes that patch to `config.d/10-dotfiles.json` and
  the ignored `settings.local.json` overlay to `config.d/90-dotfiles.local.json`.
  Dux loads the base first, then drop-ins in lexical order. Later values replace
  entire top-level objects and arrays; main settings do not use recursive merging.
- Apply removes duplicate managed keys from the base, including keys removed
  from the previous shared drop-in. Unmanaged base settings and other drop-ins
  remain intact. New GUI settings in the base are candidates for explicit capture.
- Dux writes GUI edits to the last file that owns a setting. Capture those edits
  before applying repository changes, including background convergence, or the
  managed drop-ins will be replaced by repository intent.
- `dms-settings capture` reads the effective native settings and offers to commit
  each changed patch. Keys owned by local overrides or other drop-ins stay out
  of shared capture; existing shared values hidden by them are retained.
- Display identifiers, histories, GPU selection, and migration state are excluded
  from capture. Apply preserves nested bar, dock, and desktop-widget machine
  fields by instance ID in the writable shared drop-in. A local array override
  replaces the whole array and must include its own display selections.
- Creating `config.d` requires one DMS restart for discovery. Apply does not
  restart the shell. For the first migration, run `dms-settings apply` followed
  by `dms restart` in the foreground. Background installation uses `--no-migrate`
  and records a retryable failure until that migration is done. Later edits
  reload through Dux's watchers.
- `clsettings.patch.json` and `plugin_settings.patch.json` remain separate:
  native shell drop-ins do not cover them. Apply replaces their portable settings
  and recursively merges each ignored `<name>.local.json` overlay. Capture retains
  shared values hidden by local top-level keys. Clipboard contents and runtime
  state never enter Git; KDE Connect device selection belongs in the local overlay.
- Auxiliary live files sit beside `--live`; patches and local overrides sit beside
  `--patch` and `--local-patch`. An auxiliary family is skipped only when its live
  file, tracked patch, and local override are all absent. Clipboard backend
  preferences take effect when DMS next loads them.
- Capture exports managed Git plugins and exact revisions to `plugins.lock.json`
  beside `--patch`. Apply restores them through `dms plugins restore` before
  writing settings, without pruning extra installed plugins. Restore may use the
  network and partially complete before an error; settings remain untouched if
  it fails. Plugin revisions are not upgraded implicitly.
- `plugins.lock.local.json` beside `--local-patch` replaces whole shared entries
  by plugin ID on apply. Those IDs are excluded from capture, preserving their
  existing shared entries. Keep private plugin settings in the local overlay too.
- `--settings-only` skips plugin capture and restore. Background installation uses
  it to stay network-free. Lockfiles exclude system plugins and directories
  without Git provenance. DMS owns its live lockfile; never symlink it into Git.
- Dux migrates live `DankMaterialShell` directories to `dms`, leaving compatibility
  symlinks. The helper moves ignored checkout overrides from the old path before
  capture or apply and stops on conflicts. The installer requires the new
  `dms/.firstlaunch` marker, so older desktops do not receive 2.0 settings.

DMS's `~/.config/hypr/dms/binds-user.lua` remains a narrow exception: it contains
only user keybind overrides and is linked directly into Git. Control Center
edits intentionally dirty the repository. Keep it to `hl.bind`/`hl.unbind`
statements; put logic in a tracked module such as `.config/hypr/monitor-dir.lua`.

Settings capture is explicit. Background startup applies repository changes but
never writes shared preferences back to the repository.

## Agent skills

`skills/` is the tool-neutral source for user-level agent skills. `skill-sync` links
each skill individually into `~/.claude/skills/` and `~/.codex/skills/`, leaving room
for tool-managed or local-only skills. It runs from `install.sh`, including when
background convergence detects changed skills.

## Validation

- `./readiness.sh`: read-only inventory of expected commands and platform dependencies.
- `bash -n install.sh`: installer syntax.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_artifacts.py`:
  download integrity, atomic replacement, and safe deployment staging.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_private_sync.py tests/test_secret_sync.py`: personal-host gates, local secret materialization, and encrypted sync preservation (temporary local rclone backend; no vault or cloud access).
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_dms_settings.py`: Dux native precedence,
  capture, local migration, auxiliary replacement, and atomic-write behavior.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_aconf.py`: system-layer
  gating, apply ordering, and configuration scope regressions.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_init.py`: fresh-machine
  entry point.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_dotfiles_update.py`:
  update gating, locking, retry, and timeout behavior with local Git repositories.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_install.py`: installer
  behavior in temporary repository/HOME copies with network and system setup stubbed.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_zmux.py`: session startup
  fallback and failed-session reset with process stubs. Set `ZMUX_INTEGRATION=1`
  to also exercise real Zellij resurrection and reset in an isolated HOME.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_fish_startup.py`: local
  override migration, precedence, and background environment in isolated shells.
- `./aconf.sh lint`: compiles the aconfmgr configuration. Arch personal hosts only.
- `git diff --check`: whitespace errors.

Run the smallest relevant checks. Do not run `install.sh` merely as a test: it mutates
the current home directory and may perform network or system setup. Never run
`./aconf.sh apply` as a test: it converges the live system.

## Key decisions

**No fisher/tide**: starship was chosen because it's shell-agnostic — same config on every
machine, no plugin state to manage or accidentally commit.

**fish_variables not tracked**: mixes runtime state with config and can contain secrets
via `set -U`. Anything worth persisting lives in explicit config files.

**Third-party assets are mirrored, not tracked**: `dots-sh/artifacts.json` pins
installer downloads by SHA-256. `dots-sh/artifacts.py` fetches them from
`dots.oag.sh/assets/`, verifies before atomic replacement, and stages the ignored
`dots-sh/public/` deployment. Preserve old manifest entries and immutable paths.
Deploy and verify new assets before publishing client changes. The endpoint is
static-only; `init.sh` changes require deployment too. See `dots-sh/README.md`.
Background installation never fetches assets. Git and package repositories remain
upstream dependencies.

**DMS settings are sparse patches**: the GUI remains the editor, machine state remains
local, and Git records only intentional deviations from upstream defaults.

**hx/helix aliased dynamically**: binary name differs across platforms. `config.fish`
detects whichever exists and aliases the other so EDITOR works everywhere.
